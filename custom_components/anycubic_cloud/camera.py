"""Anycubic Cloud – HLS camera entity."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    COORDINATOR,
    DOMAIN,
    PrinterEntityType,
)
from .coordinator import AnycubicCloudDataUpdateCoordinator
from .entity import AnycubicCloudEntity, AnycubicCloudEntityDescription

if TYPE_CHECKING:
    from .anycubic_cloud_api.data_models.orders import AnycubicCameraToken
    from .anycubic_cloud_api.data_models.printer import AnycubicPrinter


_LOGGER = logging.getLogger(__name__)
_REFRESH = timedelta(minutes=55)


CAMERA_TYPES: list[AnycubicCloudEntityDescription] = [
    AnycubicCloudEntityDescription(
        key="camera_stream",  # stable key -> unique_id ends _camera
        translation_key="camera",
        printer_entity_type=PrinterEntityType.PRINTER,
        requires_peripheral_camera=False,
    )
]


def _get_stream_url(token: AnycubicCameraToken) -> str | None:
    """Return HLS streaming URL for the given token."""
    kvs = boto3.client(
        "kinesisvideo",
        region_name=token.region or "us-west-2",
        aws_access_key_id=token.secret_id,
        aws_secret_access_key=token.secret_key,
        aws_session_token=token.session_token,
    )

    streams = kvs.list_streams(MaxResults=1).get("StreamInfoList") or []
    if not streams:
        return None

    stream_name = streams[0]["StreamName"]
    endpoint = kvs.get_data_endpoint(
        StreamName=stream_name,
        APIName="GET_HLS_STREAMING_SESSION_URL",
    )["DataEndpoint"]
    kav = boto3.client(
        "kinesis-video-archived-media",
        endpoint_url=endpoint,
        region_name=token.region or "us-west-2",
        aws_access_key_id=token.secret_id,
        aws_secret_access_key=token.secret_key,
        aws_session_token=token.session_token,
    )
    return kav.get_hls_streaming_session_url(
        StreamName=stream_name,
        PlaybackMode="LIVE",
        DiscontinuityMode="ALWAYS",
    )["HLSStreamingSessionURL"]


def _get_snapshot(token: AnycubicCameraToken) -> bytes | None:
    """Return a JPEG snapshot for the given token."""
    kvs = boto3.client(
        "kinesisvideo",
        region_name=token.region or "us-west-2",
        aws_access_key_id=token.secret_id,
        aws_secret_access_key=token.secret_key,
        aws_session_token=token.session_token,
    )

    streams = kvs.list_streams(MaxResults=1).get("StreamInfoList") or []
    if not streams:
        return None

    stream_name = streams[0]["StreamName"]
    endpoint = kvs.get_data_endpoint(
        StreamName=stream_name,
        APIName="GET_IMAGES",
    )["DataEndpoint"]
    kav = boto3.client(
        "kinesis-video-archived-media",
        endpoint_url=endpoint,
        region_name=token.region or "us-west-2",
        aws_access_key_id=token.secret_id,
        aws_secret_access_key=token.secret_key,
        aws_session_token=token.session_token,
    )

    now = datetime.utcnow()
    images = kav.get_images(
        StreamName=stream_name,
        ImageSelectorType="SERVER_TIMESTAMP",
        StartTimestamp=now - timedelta(seconds=1),
        EndTimestamp=now,
        Format="JPEG",
        MaxResults=1,
    ).get("Images") or []
    if not images:
        return None
    return images[0].get("ImageContent")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Anycubic Cloud camera from a config entry."""

    coordinator: AnycubicCloudDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]

    coordinator.add_entities_for_seen_printers(
        async_add_entities=async_add_entities,
        entity_constructor=AnycubicCloudCamera,
        platform=Platform.CAMERA,
        available_descriptors=CAMERA_TYPES,
    )


class AnycubicCloudCamera(AnycubicCloudEntity, Camera):
    """HA camera streaming Anycubic’s cloud feed."""

    _attr_is_streaming = True
    entity_description: AnycubicCameraEntityDescription

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: AnycubicCloudDataUpdateCoordinator,
        printer_id: int,
        entity_description: AnycubicCameraEntityDescription,
    ) -> None:
        """Initialize the Anycubic Cloud camera."""
        AnycubicCloudEntity.__init__(
            self,
            hass,
            coordinator,
            printer_id,
            entity_description,
        )
        Camera.__init__(self)

        self._stream_url: str | None = None
        self._token: AnycubicCameraToken | None = None
        self._refresh_coordinator: DataUpdateCoordinator | None = None

        printer = self.coordinator.get_printer_for_id(printer_id)
        if printer:
            self._attr_unique_id = f"{printer.machine_mac}_camera"
        self._attr_name = "Camera"

    async def async_added_to_hass(self) -> None:
        await self._refresh()
        self._refresh_coordinator = DataUpdateCoordinator(
            self.hass,
            _LOGGER,
            name="anycubic_camera_refresh",
            update_method=self._refresh,
            update_interval=_REFRESH,
        )
        await self._refresh_coordinator.async_config_entry_first_refresh()

    async def _refresh(self) -> None:
        """(Re)fetch signed HLS URL via CAMERA_OPEN."""
        printer: AnycubicPrinter | None = self.coordinator.get_printer_for_id(self._printer_id)
        if not printer:
            return

        try:
            token = await self.coordinator.anycubic_api._send_anycubic_camera_open_order(printer)
            if not token:
                _LOGGER.debug("[%s] No camera token available", printer.name)
                return
            self._token = token
            stream_url = await self.hass.async_add_executor_job(_get_stream_url, token)
            if not stream_url:
                _LOGGER.debug("[%s] No camera stream available", printer.name)
                return
            self._stream_url = stream_url
            _LOGGER.debug("[%s] HLS URL refreshed", printer.name)
        except (BotoCoreError, ClientError, Exception) as exc:  # pylint: disable=broad-except
            _LOGGER.warning("Camera refresh failed: %s", exc)

    async def stream_source(self) -> str | None:
        if not self._stream_url:
            await self._refresh()
        return self._stream_url

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image from the camera."""
        if not self._stream_url or not self._token:
            await self._refresh()

        printer: AnycubicPrinter | None = self.coordinator.get_printer_for_id(
            self._printer_id
        )
        if not printer or not self._token:
            return None

        try:
            return await self.hass.async_add_executor_job(
                _get_snapshot, self._token
            )
        except (BotoCoreError, ClientError, Exception) as exc:  # pylint: disable=broad-except

            _LOGGER.warning(
                "Failed to fetch camera image for %s: %s", printer.name, exc
            )
            return None
