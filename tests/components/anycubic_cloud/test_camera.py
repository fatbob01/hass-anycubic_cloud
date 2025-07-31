import asyncio
import sys
import types
from dataclasses import dataclass
from enum import Enum, IntEnum
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub minimal Home Assistant environment
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]
PACKAGE_PATH = ROOT / "custom_components" / "anycubic_cloud"
sys.path.append(str(ROOT))

pkg = types.ModuleType("custom_components.anycubic_cloud")
pkg.__path__ = [str(PACKAGE_PATH)]
sys.modules["custom_components.anycubic_cloud"] = pkg

class Platform(str, Enum):
    BINARY_SENSOR = "binary_sensor"
    BUTTON = "button"
    CAMERA = "camera"
    IMAGE = "image"
    SENSOR = "sensor"
    SWITCH = "switch"
    UPDATE = "update"
ha_const = types.ModuleType("homeassistant.const")
ha_const.Platform = Platform
sys.modules["homeassistant.const"] = ha_const

ha_core = types.ModuleType("homeassistant.core")
class HomeAssistant:
    def __init__(self):
        self.loop = asyncio.get_event_loop()
    async def async_add_executor_job(self, func, *args):
        return await self.loop.run_in_executor(None, func, *args)
ha_core.HomeAssistant = HomeAssistant
sys.modules["homeassistant.core"] = ha_core

ha_cam = types.ModuleType("homeassistant.components.camera")
class Camera:
    def __init__(self):
        pass
ha_cam.Camera = Camera
sys.modules["homeassistant.components.camera"] = ha_cam

ha_config_entries = types.ModuleType("homeassistant.config_entries")
class ConfigEntry:
    pass
ha_config_entries.ConfigEntry = ConfigEntry
sys.modules["homeassistant.config_entries"] = ha_config_entries

ha_entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
ha_entity_platform.AddEntitiesCallback = object
sys.modules["homeassistant.helpers.entity_platform"] = ha_entity_platform

ha_update = types.ModuleType("homeassistant.helpers.update_coordinator")
class DataUpdateCoordinator:
    pass
class CoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator
ha_update.DataUpdateCoordinator = DataUpdateCoordinator
ha_update.CoordinatorEntity = CoordinatorEntity
sys.modules["homeassistant.helpers.update_coordinator"] = ha_update

ha_entity = types.ModuleType("homeassistant.helpers.entity")
class Entity:
    pass
class EntityDescription:
    pass
ha_entity.Entity = Entity
ha_entity.EntityDescription = EntityDescription
sys.modules["homeassistant.helpers.entity"] = ha_entity

ha_device = types.ModuleType("homeassistant.helpers.device_registry")
class DeviceInfo:
    pass
ha_device.DeviceInfo = DeviceInfo
ha_device.CONNECTION_NETWORK_MAC = "mac"
sys.modules["homeassistant.helpers.device_registry"] = ha_device

helpers_mod = types.ModuleType("custom_components.anycubic_cloud.helpers")
helpers_mod.build_printer_device_info = lambda data, pid: object()
helpers_mod.printer_entity_unique_id = lambda coordinator, pid, key: f"{pid}_{key}"
sys.modules["custom_components.anycubic_cloud.helpers"] = helpers_mod

entity_mod = types.ModuleType("custom_components.anycubic_cloud.entity")
@dataclass(frozen=True)
class AnycubicCloudEntityDescription:
    key: str
    translation_key: str | None = None
    printer_entity_type: int | None = None
    requires_peripheral_camera: bool = False
class AnycubicCloudEntity:
    def __init__(self, hass, coordinator, printer_id, entity_description):
        self.hass = hass
        self.coordinator = coordinator
        self._printer_id = printer_id
        self.entity_description = entity_description
entity_mod.AnycubicCloudEntity = AnycubicCloudEntity
entity_mod.AnycubicCloudEntityDescription = AnycubicCloudEntityDescription
sys.modules["custom_components.anycubic_cloud.entity"] = entity_mod

coord_mod = types.ModuleType("custom_components.anycubic_cloud.coordinator")
class AnycubicCloudDataUpdateCoordinator:
    pass
coord_mod.AnycubicCloudDataUpdateCoordinator = AnycubicCloudDataUpdateCoordinator
sys.modules["custom_components.anycubic_cloud.coordinator"] = coord_mod

const_mod = types.ModuleType("custom_components.anycubic_cloud.const")
class PrinterEntityType(IntEnum):
    PRINTER = 2
const_mod.COORDINATOR = "coordinator"
const_mod.DOMAIN = "anycubic_cloud"
const_mod.PrinterEntityType = PrinterEntityType
sys.modules["custom_components.anycubic_cloud.const"] = const_mod

from custom_components.anycubic_cloud import camera

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_async_camera_image_success():
    hass = HomeAssistant()
    token = object()
    printer = SimpleNamespace(name="Printer", machine_mac="mac")

    coordinator = MagicMock()
    coordinator.get_printer_for_id.return_value = printer
    coordinator.anycubic_api = MagicMock()
    coordinator.data = {"printers": {1: {"states": {"id": 1, "machine_name": "m", "name": "Printer", "machine_mac": "mac", "fw_version": "1"}, "attributes": {}}}, "user_info": {"id": 1}}

    cam = camera.AnycubicCloudCamera(hass, coordinator, 1, camera.CAMERA_TYPES[0])
    cam._stream_url = "stream"
    cam._token = token

    with patch("custom_components.anycubic_cloud.camera._get_snapshot", return_value=b"img") as mock_snap:
        result = await cam.async_camera_image()
    assert result == b"img"
    mock_snap.assert_called_once_with(token)


@pytest.mark.asyncio
async def test_async_camera_image_error(caplog):
    hass = HomeAssistant()
    token = object()
    printer = SimpleNamespace(name="Printer", machine_mac="mac")

    coordinator = MagicMock()
    coordinator.get_printer_for_id.return_value = printer
    coordinator.anycubic_api = MagicMock()
    coordinator.data = {"printers": {1: {"states": {"id": 1, "machine_name": "m", "name": "Printer", "machine_mac": "mac", "fw_version": "1"}, "attributes": {}}}, "user_info": {"id": 1}}

    cam = camera.AnycubicCloudCamera(hass, coordinator, 1, camera.CAMERA_TYPES[0])
    cam._stream_url = "stream"
    cam._token = token

    with patch("custom_components.anycubic_cloud.camera._get_snapshot", side_effect=RuntimeError("boom")):
        result = await cam.async_camera_image()
    assert result is None
    assert "Printer" in caplog.text
    assert "boom" in caplog.text
