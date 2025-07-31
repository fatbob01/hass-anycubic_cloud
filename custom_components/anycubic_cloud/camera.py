"""Anycubic Cloud – HLS camera entity."""

from __future__ import annotations

import logging
from datetime import timedelta

import boto3
from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import AnycubicCloudAPI
from .const import COORDINATOR, DOMAIN
from .anycubic_cloud_api.data_models.printer import AnycubicPrinter
from .coordinator import AnycubicCloudDataUpdateCoordinator
from .helpers import build_printer_device_info

_LOGGER = logging.getLogger(__name__)
_REFRESH = timedelta(minutes=55)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: AnycubicCloudDataUpdateCoordinator = data[COORDINATOR]
    api: AnycubicCloudAPI = data["api"]
    printers = [p for p in data["printers"] if p and p.has_peripheral_camera()]

    cams = [AnycubicCloudCamera(printer, api, coordinator) for printer in printers]
    async_add_entities(cams, update_before_add=True)


class AnycubicCloudCamera(Camera):
    """HA camera streaming Anycubic’s cloud feed."""

    _attr_is_streaming = True

    def __init__(
        self,
        printer: AnycubicPrinter,
        api: AnycubicCloudAPI,
        coordinator: AnycubicCloudDataUpdateCoordinator,
    ) -> None:
        super().__init__()
        self._printer = printer
        self._api = api
        self._attr_device_info = build_printer_device_info(coordinator.data, printer.id)
        self._stream_url: str | None = None
        self._coordinator: DataUpdateCoordinator | None = None
        self._attr_name = f"{printer.name} Camera"
        self._attr_unique_id = f"{printer.machine_mac}_camera"

    async def async_added_to_hass(self) -> None:
        await self._refresh()
        self._coordinator = DataUpdateCoordinator(
            self.hass,
            _LOGGER,
            name="anycubic_camera_refresh",
            update_method=self._refresh,
            update_interval=_REFRESH,
        )
        await self._coordinator.async_config_entry_first_refresh()

    async def _refresh(self) -> None:
        """(Re)fetch signed HLS URL via CAMERA_OPEN."""
        try:
            token = await self._api._send_anycubic_camera_open_order(self._printer)
            if not token:
                return
            kvs = boto3.client(
                "kinesisvideo",
                region_name=token.region or "us-west-2",
                aws_access_key_id=token.secret_id,
                aws_secret_access_key=token.secret_key,
                aws_session_token=token.session_token,
            )
            stream_name = kvs.list_streams(MaxResults=1)["StreamInfoList"][0]["StreamName"]
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
            self._stream_url = kav.get_hls_streaming_session_url(
                StreamName=stream_name,
                PlaybackMode="LIVE",
                DiscontinuityMode="ALWAYS",
            )["HLSStreamingSessionURL"]
            _LOGGER.debug("[%s] HLS URL refreshed", self._printer.name)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning("Camera refresh failed: %s", exc)

    async def stream_source(self) -> str | None:
        if not self._stream_url:
            await self._refresh()
        return self._stream_url
