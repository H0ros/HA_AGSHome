"""Client Tuya local pour la centrale AGSHome."""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Callable

import tinytuya

from .const import (
    DEFAULT_PORT,
    DEFAULT_PROTOCOL,
    DP_MASTER_STATE,
)

_LOGGER = logging.getLogger(__name__)

RECONNECT_DELAY = 10  # secondes avant reconnexion


class AGSHomeClient:
    """Gère la connexion locale Tuya avec la centrale AGSHome."""

    def __init__(
        self,
        device_id: str,
        local_key: str,
        host: str,
        protocol: str = DEFAULT_PROTOCOL,
        callback: Callable | None = None,
    ) -> None:
        self.device_id = device_id
        self.local_key = local_key
        self.host = host
        self.protocol = protocol
        self.callback = callback

        self._device: tinytuya.Device | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._dps_cache: dict[str, Any] = {}

    def _make_device(self) -> tinytuya.Device:
        """Instancie le device TinyTuya."""
        dev = tinytuya.Device(
            dev_id=self.device_id,
            address=self.host,
            local_key=self.local_key,
            version=self.protocol,
        )
        dev.set_socketPersistent(True)
        dev.set_socketRetryLimit(3)
        dev.set_socketTimeout(5)
        return dev

    # ─── Connexion / Déconnexion ───────────────────────────────────────────

    async def connect(self) -> bool:
        """Teste la connexion et lit l'état initial."""
        try:
            device = self._make_device()
            status = await asyncio.get_event_loop().run_in_executor(
                None, device.status
            )
            if status and "dps" in status:
                self._dps_cache = status["dps"]
                _LOGGER.info("Connexion AGSHome OK — DPS initiaux: %s", self._dps_cache)
                return True
            _LOGGER.error("Réponse inattendue lors du test connexion: %s", status)
            return False
        except Exception as err:
            _LOGGER.error("Échec connexion AGSHome (%s): %s", self.host, err)
            return False

    def disconnect(self) -> None:
        """Arrête l'écoute en arrière-plan."""
        self._running = False

    # ─── Écoute en arrière-plan ───────────────────────────────────────────

    def start_listener(self, loop: asyncio.AbstractEventLoop) -> None:
        """Lance le thread d'écoute des push Tuya."""
        self._loop = loop
        self._running = True
        self._thread = threading.Thread(
            target=self._listen_loop, name="agshome_listener", daemon=True
        )
        self._thread.start()

    def _listen_loop(self) -> None:
        """Boucle bloquante (thread) qui reçoit les push Tuya."""
        _LOGGER.debug("Thread d'écoute AGSHome démarré")
        while self._running:
            try:
                device = self._make_device()
                # Lire l'état initial
                status = device.status()
                if status and "dps" in status:
                    self._on_dps_update(status["dps"])

                # Boucle de réception des push
                while self._running:
                    data = device.heartbeat(nowait=False)
                    if data is None:
                        continue
                    if "dps" in data:
                        self._on_dps_update(data["dps"])
                    elif "Error" in data:
                        _LOGGER.warning("Erreur Tuya reçue: %s", data)
                        break

            except Exception as err:
                _LOGGER.warning("Erreur listener AGSHome: %s — reconnexion dans %ds", err, RECONNECT_DELAY)
                if self._running:
                    import time
                    time.sleep(RECONNECT_DELAY)

        _LOGGER.debug("Thread d'écoute AGSHome arrêté")

    def _on_dps_update(self, dps: dict) -> None:
        """Appelé à chaque mise à jour DPS reçue."""
        # Convertir les clés int en str pour uniformité
        normalized = {str(k): v for k, v in dps.items()}
        changed = {k: v for k, v in normalized.items() if self._dps_cache.get(k) != v}
        if not changed:
            return
        self._dps_cache.update(normalized)
        _LOGGER.debug("DPS mis à jour: %s", changed)

        if self.callback and self._loop:
            asyncio.run_coroutine_threadsafe(
                self.callback(normalized), self._loop
            )

    # ─── Commandes ────────────────────────────────────────────────────────

    async def send_command(self, dp: int, value: Any) -> bool:
        """Envoie une commande Tuya (DPS)."""
        try:
            device = self._make_device()
            payload = {dp: value}
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: device.set_multiple_values(payload)
            )
            _LOGGER.debug("Commande envoyée DP%d=%s → %s", dp, value, result)
            return True
        except Exception as err:
            _LOGGER.error("Erreur envoi commande DP%d=%s: %s", dp, value, err)
            return False

    async def set_alarm_state(self, tuya_state: str) -> bool:
        """Arme ou désarme la centrale (DP 1)."""
        return await self.send_command(DP_MASTER_STATE, tuya_state)

    async def trigger_siren(self, active: bool) -> bool:
        """Active ou coupe la sirène manuellement (DP 4)."""
        from .const import DP_SIREN_ACTIVE
        return await self.send_command(DP_SIREN_ACTIVE, active)

    # ─── Lecture cache ────────────────────────────────────────────────────

    def get_dps(self) -> dict[str, Any]:
        """Retourne le dernier état connu de tous les DPS."""
        return dict(self._dps_cache)

    def get_dp(self, dp: int | str, default: Any = None) -> Any:
        """Retourne la valeur d'un DP précis depuis le cache."""
        return self._dps_cache.get(str(dp), default)
