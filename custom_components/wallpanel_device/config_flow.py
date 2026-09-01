"""Config flow for WallPanel Device."""

from typing import Any, override

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WallPanelApiClient, WallPanelApiError
from .const import (
    CONF_DEVICE_NAME,
    CONF_MQTT_BASE_TOPIC,
    CONF_MQTT_CLIENT_ID,
    CONF_REMOVE_NATIVE_DISCOVERY,
    DEFAULT_PORT,
    DOMAIN,
    LOGGER,
)


def _normalize_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Normalize user-provided connection values."""
    data = dict(user_input)
    data[CONF_HOST] = str(data[CONF_HOST]).strip().removeprefix("http://").rstrip("/")
    data[CONF_MQTT_CLIENT_ID] = str(data[CONF_MQTT_CLIENT_ID]).strip()
    data[CONF_MQTT_BASE_TOPIC] = (
        str(data[CONF_MQTT_BASE_TOPIC]).strip().strip("/") + "/"
    )
    data[CONF_DEVICE_NAME] = str(data[CONF_DEVICE_NAME]).strip()
    return data


async def _async_validate_input(
    hass: HomeAssistant, user_input: dict[str, Any]
) -> None:
    """Validate access to WallPanel's state endpoint."""
    client = WallPanelApiClient(
        async_get_clientsession(hass),
        user_input[CONF_HOST],
        user_input[CONF_PORT],
    )
    await client.async_get_state()


class WallPanelDeviceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle WallPanel Device configuration."""

    VERSION = 1

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle user setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = _normalize_input(user_input)
            try:
                await _async_validate_input(self.hass, user_input)
            except WallPanelApiError as err:
                LOGGER.debug("WallPanel validation failed: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unexpected WallPanel validation error")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_MQTT_CLIENT_ID])
                self._abort_if_unique_id_configured(
                    updates={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                    }
                )
                return self.async_create_entry(
                    title=user_input[CONF_DEVICE_NAME], data=user_input
                )

        defaults = user_input or {}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_NAME,
                        default=defaults.get(CONF_DEVICE_NAME, "WallPanel"),
                    ): str,
                    vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
                    vol.Required(
                        CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
                    vol.Required(
                        CONF_MQTT_CLIENT_ID,
                        default=defaults.get(CONF_MQTT_CLIENT_ID, ""),
                    ): str,
                    vol.Required(
                        CONF_MQTT_BASE_TOPIC,
                        default=defaults.get(CONF_MQTT_BASE_TOPIC, "wallpanel/"),
                    ): str,
                    vol.Optional(
                        CONF_REMOVE_NATIVE_DISCOVERY,
                        default=defaults.get(CONF_REMOVE_NATIVE_DISCOVERY, True),
                    ): bool,
                }
            ),
            errors=errors,
        )

    @override
    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reconfigure an existing WallPanel entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = _normalize_input(user_input)
            try:
                await _async_validate_input(self.hass, user_input)
            except WallPanelApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unexpected WallPanel reconfiguration error")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_MQTT_CLIENT_ID])
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=user_input,
                    title=user_input[CONF_DEVICE_NAME],
                )

        suggested = user_input or dict(entry.data)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_DEVICE_NAME): str,
                        vol.Required(CONF_HOST): str,
                        vol.Required(CONF_PORT): vol.All(
                            vol.Coerce(int), vol.Range(min=1, max=65535)
                        ),
                        vol.Required(CONF_MQTT_CLIENT_ID): str,
                        vol.Required(CONF_MQTT_BASE_TOPIC): str,
                        vol.Optional(CONF_REMOVE_NATIVE_DISCOVERY): bool,
                    }
                ),
                suggested,
            ),
            errors=errors,
        )
