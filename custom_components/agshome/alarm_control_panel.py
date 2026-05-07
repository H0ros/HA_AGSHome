"""Plateforme AlarmControlPanel pour AGSHome."""
from __future__ import annotations

import logging

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
    CodeFormat,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_HOST,
    DOMAIN,
    DP_MASTER_STATE,
    DP_DETAILED_STATE,
    HA_TO_TUYA_CMD,
    SIGNAL_UPDATE,
    TUYA_TO_HA_STATE,
)
from .coordinator import AGSHomeCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure l'entité alarme."""
    coordinator: AGSHomeCoordinator = hass.data[DOMAIN][entry.entry_id]["hub"]
    async_add_entities(
        [AGSHomeAlarmPanel(coordinator, entry)],
        update_before_add=True,
    )


class AGSHomeAlarmPanel(AlarmControlPanelEntity):
    """Centrale d'alarme AGSHome."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_name = "Alarme"
    _attr_code_format = CodeFormat.NUMBER
    _attr_code_arm_required = False  # Le code n'est pas requis depuis HA (géré en local)

    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.TRIGGER
    )

    def __init__(self, coordinator: AGSHomeCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"agshome_alarm_{entry.data['device_id']}"
        self._state: AlarmControlPanelState = AlarmControlPanelState.DISARMED
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data["device_id"])},
            name="AGSHome Alarm",
            manufacturer="AGSHome",
            model="WiFi Alarm Hub",
            sw_version=entry.data.get("protocol_version", "3.3"),
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )

    async def async_added_to_hass(self) -> None:
        """S'abonne aux mises à jour."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self._handle_update)
        )
        self._refresh_state()

    @callback
    def _handle_update(self, dps: dict) -> None:
        """Appelé à chaque mise à jour DPS."""
        self._refresh_state()
        self.async_write_ha_state()

    def _refresh_state(self) -> None:
        """Lit le dernier état depuis le coordinateur."""
        # Priorité : DP1 (master_state string), sinon DP101 (détaillé)
        raw = self._coordinator.get_dp(DP_MASTER_STATE) or self._coordinator.get_dp(DP_DETAILED_STATE)
        if raw is None:
            return

        ha_state_str = TUYA_TO_HA_STATE.get(str(raw).lower()) or TUYA_TO_HA_STATE.get(str(raw))
        if ha_state_str == "disarmed":
            self._state = AlarmControlPanelState.DISARMED
        elif ha_state_str == "armed_away":
            self._state = AlarmControlPanelState.ARMED_AWAY
        elif ha_state_str == "armed_home":
            self._state = AlarmControlPanelState.ARMED_HOME
        elif ha_state_str == "triggered":
            self._state = AlarmControlPanelState.TRIGGERED
        else:
            _LOGGER.debug("État Tuya non mappé: %s", raw)

    @property
    def alarm_state(self) -> AlarmControlPanelState:
        return self._state

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Désarme l'alarme."""
        await self._coordinator.client.set_alarm_state(HA_TO_TUYA_CMD["disarm"])
        self._state = AlarmControlPanelState.DISARMED
        self.async_write_ha_state()

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Armement total (away)."""
        await self._coordinator.client.set_alarm_state(HA_TO_TUYA_CMD["arm_away"])
        self._state = AlarmControlPanelState.ARMED_AWAY
        self.async_write_ha_state()

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Armement partiel (home)."""
        await self._coordinator.client.set_alarm_state(HA_TO_TUYA_CMD["arm_home"])
        self._state = AlarmControlPanelState.ARMED_HOME
        self.async_write_ha_state()

    async def async_alarm_trigger(self, code: str | None = None) -> None:
        """Déclenche la sirène manuellement (panic)."""
        await self._coordinator.client.trigger_siren(True)
        self._state = AlarmControlPanelState.TRIGGERED
        self.async_write_ha_state()
