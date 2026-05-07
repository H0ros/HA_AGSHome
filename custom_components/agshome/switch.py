"""Plateforme Switch pour AGSHome — contrôles caméra (LED vision nocturne, retournement)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_CAMERA_DEVICE_ID,
    DOMAIN,
    DP_CAM_FLIP,
    DP_CAM_LIGHT,
    SIGNAL_CAMERA_UPDATE,
)
from .coordinator import AGSHomeCameraCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure les switchs caméra si une caméra est présente."""
    cam_coordinator: AGSHomeCameraCoordinator | None = hass.data[DOMAIN][entry.entry_id].get("camera")
    if cam_coordinator is None:
        return

    device_id = entry.data.get(CONF_CAMERA_DEVICE_ID, "camera")
    async_add_entities([
        AGSHomeCameraSwitch(
            coordinator=cam_coordinator,
            entry=entry,
            device_id=device_id,
            dp=DP_CAM_LIGHT,
            key="light",
            name="LED vision nocturne",
            icon="mdi:led-on",
        ),
        AGSHomeCameraSwitch(
            coordinator=cam_coordinator,
            entry=entry,
            device_id=device_id,
            dp=DP_CAM_FLIP,
            key="flip",
            name="Image retournée",
            icon="mdi:flip-vertical",
        ),
    ], update_before_add=True)


class AGSHomeCameraSwitch(SwitchEntity):
    """Switch générique pour un paramètre booléen de la caméra."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: AGSHomeCameraCoordinator,
        entry: ConfigEntry,
        device_id: str,
        dp: int,
        key: str,
        name: str,
        icon: str,
    ) -> None:
        self._coordinator = coordinator
        self._dp = dp
        self._attr_unique_id = f"agshome_cam_{device_id}_{key}"
        self._attr_name = name
        self._attr_icon = icon
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

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._is_on = True
        self.async_write_ha_state()
        await self._coordinator.client.send_command(self._dp, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._is_on = False
        self.async_write_ha_state()
        await self._coordinator.client.send_command(self._dp, False)
