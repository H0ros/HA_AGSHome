"""Gestionnaire des zones et sous-appareils de la centrale AGSHome."""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from typing import Any

from .const import (
    DP_LAST_SENSOR_STATE,
    DP_SUB_CLASS,
    DP_ZONE_NUMBER,
    DP_ZONE_TRIGGERED,
    SUB_CLASS_TO_HA,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class Zone:
    """Représente un sous-appareil / zone de la centrale."""
    zone_id: int                    # numéro de zone (DP 37)
    sub_class: str                  # type Tuya (door_sensor, pir, …)
    ha_class: str | None            # device_class HA
    name: str                       # nom affiché
    triggered: bool = False         # état alarme actuel
    last_trigger_text: str = ""     # texte décodé DP 26
    extra: dict = field(default_factory=dict)


class ZoneManager:
    """Parse les DPS hub et maintient la liste des zones connues."""

    def __init__(self) -> None:
        self._zones: dict[int, Zone] = {}   # zone_id → Zone

    # ──────────────────────────────────────────────────────────
    # API publique
    # ──────────────────────────────────────────────────────────

    def process_dps(self, dps: dict[str, Any]) -> list[int]:
        """
        Traite un batch de DPS et retourne les zone_ids modifiés.
        Appelé à chaque push du hub.
        """
        changed: list[int] = []

        # DP 37 : numéro de zone + DP 36 : type sous-appareil
        zone_number = self._get(dps, DP_ZONE_NUMBER)
        sub_class   = self._get(dps, DP_SUB_CLASS, "")

        if zone_number is not None:
            zone_id = int(zone_number)
            zone = self._get_or_create(zone_id, str(sub_class))

            # DP 32 : état du dernier capteur déclenché
            sensor_state = self._get(dps, DP_LAST_SENSOR_STATE)
            if sensor_state is not None:
                new_triggered = str(sensor_state).lower() in ("alarm", "triggered", "true", "1")
                if zone.triggered != new_triggered:
                    zone.triggered = new_triggered
                    changed.append(zone_id)

            # DP 26 : texte zone déclenché (base64 UTF-16LE)
            zone_text_b64 = self._get(dps, DP_ZONE_TRIGGERED)
            if zone_text_b64:
                decoded = self._decode_zone_text(str(zone_text_b64))
                if decoded:
                    zone.last_trigger_text = decoded
                    zone.triggered = True
                    if zone_id not in changed:
                        changed.append(zone_id)
                    _LOGGER.debug("Zone %d déclenchée : %s", zone_id, decoded)

        # Cas où DP 26 arrive sans DP 37 (certains firmwares)
        elif self._get(dps, DP_ZONE_TRIGGERED) is not None:
            zone_text_b64 = self._get(dps, DP_ZONE_TRIGGERED)
            decoded = self._decode_zone_text(str(zone_text_b64))
            zone_id_from_text = self._parse_zone_id_from_text(decoded)
            if zone_id_from_text is not None:
                zone = self._get_or_create(zone_id_from_text, str(sub_class))
                zone.triggered = True
                zone.last_trigger_text = decoded
                changed.append(zone_id_from_text)

        # Réarmement : si master_state repasse à disarmed, reset toutes les zones
        master = self._get(dps, 1)
        if master in ("disarmed", "1"):
            for z in self._zones.values():
                if z.triggered:
                    z.triggered = False
                    if z.zone_id not in changed:
                        changed.append(z.zone_id)

        return changed

    def get_zone(self, zone_id: int) -> Zone | None:
        return self._zones.get(zone_id)

    def get_all_zones(self) -> list[Zone]:
        return list(self._zones.values())

    def get_zones_by_class(self, ha_class: str) -> list[Zone]:
        return [z for z in self._zones.values() if z.ha_class == ha_class]

    def register_zone(self, zone_id: int, sub_class: str, name: str | None = None) -> Zone:
        """Enregistre manuellement une zone (depuis la config ou le cloud)."""
        zone = self._get_or_create(zone_id, sub_class)
        if name:
            zone.name = name
        return zone

    # ──────────────────────────────────────────────────────────
    # Helpers privés
    # ──────────────────────────────────────────────────────────

    def _get_or_create(self, zone_id: int, sub_class: str) -> Zone:
        if zone_id not in self._zones:
            ha_class = SUB_CLASS_TO_HA.get(sub_class.lower())
            self._zones[zone_id] = Zone(
                zone_id=zone_id,
                sub_class=sub_class,
                ha_class=ha_class,
                name=self._default_name(zone_id, sub_class),
            )
            _LOGGER.info("Nouvelle zone découverte : %d (%s → %s)", zone_id, sub_class, ha_class)
        else:
            # Mettre à jour sub_class si on reçoit une info plus précise
            zone = self._zones[zone_id]
            if sub_class and sub_class != zone.sub_class:
                zone.sub_class = sub_class
                zone.ha_class = SUB_CLASS_TO_HA.get(sub_class.lower())
        return self._zones[zone_id]

    @staticmethod
    def _default_name(zone_id: int, sub_class: str) -> str:
        labels = {
            "door_sensor":       "Porte/Fenêtre",
            "pir":               "Détecteur mouvement",
            "pir_sensor":        "Détecteur mouvement",
            "motion_sensor":     "Détecteur mouvement",
            "smoke_sensor":      "Détecteur fumée",
            "water_sensor":      "Détecteur eau",
            "sos_button":        "Bouton SOS",
            "remote_controller": "Télécommande",
        }
        label = labels.get(sub_class.lower(), f"Zone {zone_id}")
        return f"{label} {zone_id}"

    @staticmethod
    def _decode_zone_text(b64_str: str) -> str:
        """
        Décode le DP 26 (base64 → UTF-16LE).
        Exemple de sortie : "System Alarm\nZone: 001"
        """
        try:
            raw = base64.b64decode(b64_str)
            # Essai UTF-16LE d'abord (format observé sur PG103/PG107)
            text = raw.decode("utf-16-le", errors="ignore").strip("\x00").strip()
            if text:
                return text
            # Repli UTF-8
            return raw.decode("utf-8", errors="ignore").strip()
        except Exception as err:
            _LOGGER.debug("Impossible de décoder DP26 '%s': %s", b64_str[:30], err)
            return ""

    @staticmethod
    def _parse_zone_id_from_text(text: str) -> int | None:
        """
        Extrait le numéro de zone depuis le texte décodé du DP 26.
        Ex: "System Alarm\nZone: 001"  →  1
        """
        import re
        if not text:
            return None
        match = re.search(r"zone[:\s]+0*(\d+)", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _get(dps: dict, dp: int, default: Any = None) -> Any:
        return dps.get(str(dp), dps.get(dp, default))
