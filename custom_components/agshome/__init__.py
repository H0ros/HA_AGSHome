"""Intégration AGSHome Alarm pour Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .agshome_client import AGSHomeClient
from .const import (
    CONF_CAMERA_DEVICE_ID,
    CONF_CAMERA_HOST,
    CONF_CAMERA_LOCAL_KEY,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_LOCAL_KEY,
    CONF_PROTOCOL,
    DEFAULT_PROTOCOL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import AGSHomeCoordinator, AGSHomeCameraCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configure l'intégration depuis une entrée de configuration."""

    # ── Hub principal ──────────────────────────────────────────────────────
    hub_client = AGSHomeClient(
        device_id=entry.data[CONF_DEVICE_ID],
        local_key=entry.data[CONF_LOCAL_KEY],
        host=entry.data[CONF_HOST],
        protocol=entry.data.get(CONF_PROTOCOL, DEFAULT_PROTOCOL),
    )
    coordinator = AGSHomeCoordinator(hass, hub_client)

    ok = await coordinator.start()
    if not ok:
        raise ConfigEntryNotReady(
            f"Impossible de se connecter à la centrale AGSHome ({entry.data[CONF_HOST]})"
        )

    entry_data: dict = {"hub": coordinator, "camera": None}

    # ── Caméra (optionnelle) ───────────────────────────────────────────────
    cam_host = entry.data.get(CONF_CAMERA_HOST)
    cam_device_id = entry.data.get(CONF_CAMERA_DEVICE_ID)
    cam_local_key = entry.data.get(CONF_CAMERA_LOCAL_KEY)

    if cam_host and cam_device_id and cam_local_key:
        cam_client = AGSHomeClient(
            device_id=cam_device_id,
            local_key=cam_local_key,
            host=cam_host,
            protocol=entry.data.get(CONF_PROTOCOL, DEFAULT_PROTOCOL),
        )
        cam_coordinator = AGSHomeCameraCoordinator(hass, cam_client)
        cam_ok = await cam_coordinator.start()
        if cam_ok:
            entry_data["camera"] = cam_coordinator
            _LOGGER.info("Caméra AGSHome connectée (%s)", cam_host)
        else:
            _LOGGER.warning("Impossible de se connecter à la caméra AGSHome (%s) — ignorée", cam_host)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry_data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharge l'intégration."""
    entry_data = hass.data[DOMAIN][entry.entry_id]

    coordinator: AGSHomeCoordinator = entry_data["hub"]
    await coordinator.stop()

    cam_coordinator: AGSHomeCameraCoordinator | None = entry_data.get("camera")
    if cam_coordinator:
        await cam_coordinator.stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recharge l'entrée."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
