"""Coordinateur pour l'intégration AGSHome."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .agshome_client import AGSHomeClient
from .const import SIGNAL_UPDATE, SIGNAL_ZONE_UPDATE, SIGNAL_CAMERA_UPDATE
from .zone_manager import ZoneManager, Zone

_LOGGER = logging.getLogger(__name__)


class AGSHomeCoordinator:
    """Coordonne les données entre le client Tuya, le ZoneManager et les entités HA."""

    def __init__(self, hass: HomeAssistant, client: AGSHomeClient) -> None:
        self.hass = hass
        self.client = client
        self.zone_manager = ZoneManager()
        self._started = False
        client.callback = self._on_update

    async def start(self) -> bool:
        """Initialise la connexion et démarre l'écoute push."""
        ok = await self.client.connect()
        if not ok:
            return False
        loop = asyncio.get_event_loop()
        self.client.start_listener(loop)
        self._started = True
        return True

    async def stop(self) -> None:
        """Arrête l'écoute."""
        self.client.disconnect()
        self._started = False

    async def _on_update(self, dps: dict[str, Any]) -> None:
        """Reçoit les DPS mis à jour, met à jour les zones, notifie les entités."""
        _LOGGER.debug("Update coordinateur: %s", dps)

        # 1. Notifier toutes les entités du hub (alarme, binary_sensors, sensors)
        async_dispatcher_send(self.hass, SIGNAL_UPDATE, dps)

        # 2. Traiter les zones (DP 26, 32, 36, 37)
        changed_zones = self.zone_manager.process_dps(dps)
        for zone_id in changed_zones:
            zone = self.zone_manager.get_zone(zone_id)
            if zone:
                async_dispatcher_send(self.hass, f"{SIGNAL_ZONE_UPDATE}_{zone_id}", zone)
                # Signal générique pour détecter les nouvelles zones
                async_dispatcher_send(self.hass, SIGNAL_ZONE_UPDATE, zone)

    # ── Accès DPS hub ─────────────────────────────────────────────────────

    def get_dp(self, dp: int | str, default: Any = None) -> Any:
        return self.client.get_dp(dp, default)

    def get_all_dps(self) -> dict:
        return self.client.get_dps()

    # ── Accès zones ───────────────────────────────────────────────────────

    def get_zone(self, zone_id: int) -> Zone | None:
        return self.zone_manager.get_zone(zone_id)

    def get_all_zones(self) -> list[Zone]:
        return self.zone_manager.get_all_zones()

    def get_zones_by_class(self, ha_class: str) -> list[Zone]:
        return self.zone_manager.get_zones_by_class(ha_class)


class AGSHomeCameraCoordinator:
    """Coordinateur dédié à la caméra AGSHome (device Tuya indépendant)."""

    def __init__(self, hass: HomeAssistant, client: AGSHomeClient) -> None:
        self.hass = hass
        self.client = client
        self._started = False
        client.callback = self._on_update

    async def start(self) -> bool:
        ok = await self.client.connect()
        if not ok:
            return False
        loop = asyncio.get_event_loop()
        self.client.start_listener(loop)
        self._started = True
        return True

    async def stop(self) -> None:
        self.client.disconnect()
        self._started = False

    async def _on_update(self, dps: dict[str, Any]) -> None:
        _LOGGER.debug("Update caméra: %s", dps)
        async_dispatcher_send(self.hass, SIGNAL_CAMERA_UPDATE, dps)

    def get_dp(self, dp: int | str, default: Any = None) -> Any:
        return self.client.get_dp(dp, default)
