"""Plateforme Sensor pour AGSHome (batterie, compte à rebours, capteurs)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    DP_BATTERY_LEVEL,
    DP_COUNTDOWN,
    DP_SENSOR_COUNT,
    SIGNAL_UPDATE,
)
from .coordinator import AGSHomeCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AGSSensorDesc(SensorEntityDescription):
    dp: int = 0


SENSORS: tuple[AGSSensorDesc, ...] = (
    AGSSensorDesc(
        key="battery",
        dp=DP_BATTERY_LEVEL,
        name="Batterie de secours",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:battery",
    ),
    AGSSensorDesc(
        key="countdown",
        dp=DP_COUNTDOWN,
        name="Compte à rebours",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        icon="mdi:timer-outline",
    ),
    AGSSensorDesc(
        key="sensor_count",
        dp=DP_SENSOR_COUNT,
        name="Capteurs connectés",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:counter",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AGSHomeCoordinator = hass.data[DOMAIN][entry.entry_id]["hub"]
    async_add_entities(
        [AGSHomeSensor(coordinator, entry, desc) for desc in SENSORS],
        update_before_add=True,
    )


class AGSHomeSensor(SensorEntity):
    """Capteur numérique AGSHome."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: AGSHomeCoordinator,
        entry: ConfigEntry,
        description: AGSSensorDesc,
    ) -> None:
        self._coordinator = coordinator
        self._desc = description
        self.entity_description = description
        self._attr_unique_id = f"agshome_{entry.data['device_id']}_{description.key}"
        self._attr_native_value = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data["device_id"])},
            name="AGSHome Alarm",
            manufacturer="AGSHome",
            model="WiFi Alarm Hub",
        )

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
            try:
                self._attr_native_value = int(raw)
            except (ValueError, TypeError):
                self._attr_native_value = raw
