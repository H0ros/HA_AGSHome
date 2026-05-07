"""Config Flow pour l'intégration AGSHome."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

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
)

_LOGGER = logging.getLogger(__name__)

PROTOCOL_OPTIONS = ["3.1", "3.2", "3.3", "3.4"]


async def _test_connection(device_id: str, local_key: str, host: str, protocol: str) -> str | None:
    client = AGSHomeClient(device_id=device_id, local_key=local_key, host=host, protocol=protocol)
    try:
        ok = await client.connect()
        return None if ok else "cannot_connect"
    except Exception as err:
        _LOGGER.error("Erreur test connexion AGSHome: %s", err)
        return "cannot_connect"


class AGSHomeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Flux de configuration AGSHome en deux étapes."""

    VERSION = 1

    def __init__(self) -> None:
        self._hub_data: dict[str, Any] = {}

    # ── Étape 1 : Hub principal ───────────────────────────────────────────

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID].strip()
            local_key  = user_input[CONF_LOCAL_KEY].strip()
            host       = user_input[CONF_HOST].strip()
            protocol   = user_input.get(CONF_PROTOCOL, DEFAULT_PROTOCOL)

            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

            error = await _test_connection(device_id, local_key, host, protocol)
            if error:
                errors["base"] = error
            else:
                self._hub_data = {
                    CONF_DEVICE_ID: device_id,
                    CONF_LOCAL_KEY: local_key,
                    CONF_HOST: host,
                    CONF_PROTOCOL: protocol,
                }
                return await self.async_step_camera()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_DEVICE_ID): str,
                vol.Required(CONF_LOCAL_KEY): str,
                vol.Optional(CONF_PROTOCOL, default=DEFAULT_PROTOCOL): vol.In(PROTOCOL_OPTIONS),
            }),
            errors=errors,
        )

    # ── Étape 2 : Caméra (optionnelle) ───────────────────────────────────

    async def async_step_camera(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            cam_host       = user_input.get(CONF_CAMERA_HOST, "").strip()
            cam_device_id  = user_input.get(CONF_CAMERA_DEVICE_ID, "").strip()
            cam_local_key  = user_input.get(CONF_CAMERA_LOCAL_KEY, "").strip()

            # Si l'utilisateur a renseigné la caméra, on teste la connexion
            if cam_host and cam_device_id and cam_local_key:
                error = await _test_connection(
                    cam_device_id, cam_local_key, cam_host,
                    self._hub_data.get(CONF_PROTOCOL, DEFAULT_PROTOCOL)
                )
                if error:
                    errors["base"] = "cannot_connect_camera"
                else:
                    self._hub_data.update({
                        CONF_CAMERA_HOST: cam_host,
                        CONF_CAMERA_DEVICE_ID: cam_device_id,
                        CONF_CAMERA_LOCAL_KEY: cam_local_key,
                    })

            if not errors:
                return self.async_create_entry(
                    title=f"AGSHome {self._hub_data[CONF_HOST]}",
                    data=self._hub_data,
                )

        return self.async_show_form(
            step_id="camera",
            data_schema=vol.Schema({
                vol.Optional(CONF_CAMERA_HOST, default=""): str,
                vol.Optional(CONF_CAMERA_DEVICE_ID, default=""): str,
                vol.Optional(CONF_CAMERA_LOCAL_KEY, default=""): str,
            }),
            errors=errors,
        )
