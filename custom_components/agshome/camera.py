"""Plateforme Camera pour AGSHome — détection mouvement et état en ligne."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_CAMERA_DEVICE_ID,
    DOMAIN,
    DP_CAM_MOTION,
    DP_CAM_ONLINE,
    SIGNAL_CAMERA_UPDATE,
)
from .coordinator import AGSHomeCameraCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure les entités caméra si une caméra est configurée."""
    cam_coordinator: AGSHomeCameraCoordinator | None = hass.data[DOMAIN][entry.entry_id].get("camera")
    if cam_coordinator is None:
        return
    device_id = entry.data.get(CONF_CAMERA_DEVICE_ID, "camera")
    async_add_entities([
        AGSHomeCameraMotionSensor(cam_coordinator, entry, device_id),
        AGSHomeCameraOnlineSensor(cam_coordinator, entry, device_id),
    ], update_before_add=True)


class _CameraEntity(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, entry, device_id, dp, key):
        self._coordinator = coordinator
        self._dp = dp
        self._attr_unique_id = f"agshome_cam_{device_id}_{key}"
        self._is_on = False
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"camera_{device_id}")},
            name="AGSHome Caméra",
            manufacturer="AGSHome",
            model="WiFi Camera",
            via_device=(DOMAIN, entry.data["device_id"]),
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_CAMERA_UPDATE, self._handle_update)
        )
        self._refresh()

    @callback
    def _handle_update(self, dps: dict) -> None:
        self._refresh()
        self.async_write_ha_state()

    def _refresh(self) -> None:
        raw = self._coordinator.get_dp(self._dp)
        if raw is not None:
            self._is_on = bool(raw)

    @property
    def is_on(self) -> bool:
        return self._is_on


class AGSHomeCameraMotionSensor(_CameraEntity):
    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_name = "Mouvement caméra"
    _attr_icon = "mdi:motion-sensor"

    def __init__(self, coordinator, entry, device_id):
        super().__init__(coordinator, entry, device_id, DP_CAM_MOTION, "motion")


class AGSHomeCameraOnlineSensor(_CameraEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_name = "Caméra en ligne"
    _attr_icon = "mdi:camera-wireless"

    def __init__(self, coordinator, entry, device_id):
        super().__init__(coordinator, entry, device_id, DP_CAM_ONLINE, "online")
