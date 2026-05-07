"""Capteurs binaires dynamiques pour les zones AGSHome (portes, PIR, fumée…)."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_ZONE_UPDATE
from .coordinator import AGSHomeCoordinator
from .zone_manager import Zone

_LOGGER = logging.getLogger(__name__)

# Mapping ha_class (zone_manager) → BinarySensorDeviceClass
HA_CLASS_TO_DEVICE_CLASS: dict[str | None, BinarySensorDeviceClass] = {
    "door":     BinarySensorDeviceClass.DOOR,
    "motion":   BinarySensorDeviceClass.MOTION,
    "smoke":    BinarySensorDeviceClass.SMOKE,
    "moisture": BinarySensorDeviceClass.MOISTURE,
    "safety":   BinarySensorDeviceClass.SAFETY,
    None:       BinarySensorDeviceClass.SAFETY,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure les capteurs de zones — s'étend dynamiquement à chaque nouvelle zone."""
    coordinator: AGSHomeCoordinator = hass.data[DOMAIN][entry.entry_id]["hub"]
    added_zones: set[int] = set()

    @callback
    def _on_zone_update(zone: Zone) -> None:
        """Appelé à chaque zone mise à jour — ajoute l'entité si nouvelle."""
        # Ignorer les télécommandes et claviers (ha_class = None)
        if zone.ha_class is None:
            return
        if zone.zone_id in added_zones:
            return
        added_zones.add(zone.zone_id)
        _LOGGER.info("Nouvelle zone %d découverte (%s), ajout entité HA", zone.zone_id, zone.sub_class)
        async_add_entities([AGSHomeZoneSensor(coordinator, entry, zone)])

    # S'abonner au signal générique de zone (pour les zones découvertes en live)
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_ZONE_UPDATE, _on_zone_update)
    )

    # Ajouter immédiatement les zones déjà connues au démarrage
    for zone in coordinator.get_all_zones():
        if zone.ha_class is not None and zone.zone_id not in added_zones:
            added_zones.add(zone.zone_id)
            async_add_entities([AGSHomeZoneSensor(coordinator, entry, zone)])


class AGSHomeZoneSensor(BinarySensorEntity):
    """Capteur binaire représentant une zone (porte, PIR, fumée, SOS…)."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: AGSHomeCoordinator,
        entry: ConfigEntry,
        zone: Zone,
    ) -> None:
        self._coordinator = coordinator
        self._zone_id = zone.zone_id
        self._attr_unique_id = f"agshome_{entry.data['device_id']}_zone_{zone.zone_id}"
        self._attr_name = zone.name
        self._attr_device_class = HA_CLASS_TO_DEVICE_CLASS.get(
            zone.ha_class, BinarySensorDeviceClass.SAFETY
        )
        self._is_on = zone.triggered
        self._last_trigger_text = zone.last_trigger_text

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.data['device_id']}_zone_{zone.zone_id}")},
            name=zone.name,
            manufacturer="AGSHome",
            model=f"Capteur {zone.sub_class}",
            via_device=(DOMAIN, entry.data["device_id"]),
        )

    async def async_added_to_hass(self) -> None:
        """S'abonne aux mises à jour de cette zone spécifique."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_ZONE_UPDATE}_{self._zone_id}",
                self._handle_zone_update,
            )
        )

    @callback
    def _handle_zone_update(self, zone: Zone) -> None:
        self._is_on = zone.triggered
        self._last_trigger_text = zone.last_trigger_text
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def extra_state_attributes(self) -> dict:
        attrs: dict = {"zone_id": self._zone_id}
        if self._last_trigger_text:
            attrs["last_trigger"] = self._last_trigger_text
        zone = self._coordinator.get_zone(self._zone_id)
        if zone:
            attrs["sub_class"] = zone.sub_class
        return attrs
