"""Plateforme Binary Sensor pour AGSHome.

Gère deux groupes :
  1. Capteurs fixes du hub (sabotage, sirène, secteur, WiFi…)  — statiques
  2. Zones découvertes dynamiquement (portes, PIR…)            — délégué à zone_binary_sensor
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    DP_AC_POWER,
    DP_ALARM_TRIGGERED,
    DP_READY,
    DP_SIREN_ACTIVE,
    DP_TAMPER,
    DP_WIFI_OK,
    SIGNAL_UPDATE,
)
from .coordinator import AGSHomeCoordinator
from .zone_binary_sensor import async_setup_entry as async_setup_zone_sensors

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AGSBinarySensorDesc(BinarySensorEntityDescription):
    dp: int = 0
    invert: bool = False


HUB_BINARY_SENSORS: tuple[AGSBinarySensorDesc, ...] = (
    AGSBinarySensorDesc(
        key="tamper",
        dp=DP_TAMPER,
        name="Sabotage",
        device_class=BinarySensorDeviceClass.TAMPER,
        icon="mdi:shield-alert",
    ),
    AGSBinarySensorDesc(
        key="siren",
        dp=DP_SIREN_ACTIVE,
        name="Sirène active",
        device_class=BinarySensorDeviceClass.SOUND,
        icon="mdi:volume-high",
    ),
    AGSBinarySensorDesc(
        key="ac_power",
        dp=DP_AC_POWER,
        name="Alimentation secteur",
        device_class=BinarySensorDeviceClass.PLUG,
        icon="mdi:power-plug",
    ),
    AGSBinarySensorDesc(
        key="alarm_triggered",
        dp=DP_ALARM_TRIGGERED,
        name="Alarme déclenchée",
        device_class=BinarySensorDeviceClass.SAFETY,
        icon="mdi:alarm-light",
    ),
    AGSBinarySensorDesc(
        key="ready",
        dp=DP_READY,
        name="Système prêt",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:shield-check",
        invert=True,
    ),
    AGSBinarySensorDesc(
        key="wifi",
        dp=DP_WIFI_OK,
        name="WiFi connecté",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:wifi",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure les capteurs fixes du hub + les zones dynamiques."""
    coordinator: AGSHomeCoordinator = hass.data[DOMAIN][entry.entry_id]["hub"]

    # 1. Capteurs fixes du hub
    async_add_entities(
        [AGSHomeBinarySensor(coordinator, entry, desc) for desc in HUB_BINARY_SENSORS],
        update_before_add=True,
    )

    # 2. Zones dynamiques (portes, PIR, fumée…)
    await async_setup_zone_sensors(hass, entry, async_add_entities)


class AGSHomeBinarySensor(BinarySensorEntity):
    """Capteur binaire fixe du hub AGSHome."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: AGSHomeCoordinator,
        entry: ConfigEntry,
        description: AGSBinarySensorDesc,
    ) -> None:
        self._coordinator = coordinator
        self._desc = description
        self.entity_description = description
        self._attr_unique_id = f"agshome_{entry.data['device_id']}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data["device_id"])},
            name="AGSHome Alarm",
            manufacturer="AGSHome",
            model="WiFi Alarm Hub",
        )
        self._is_on: bool = False

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self._handle_update)
        )
        self._refresh()

    @callback
    def _handle_update(self, dps: dict) -> None:
        self._refresh()
        self.async_write_ha_state()

    def _refresh(self) -> None:
        raw = self._coordinator.get_dp(self._desc.dp)
        if raw is not None:
            state = bool(raw)
            self._is_on = (not state) if self._desc.invert else state

    @property
    def is_on(self) -> bool:
        return self._is_on
