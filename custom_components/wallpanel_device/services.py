"""Actions for WallPanel Device."""

from typing import Any

import voluptuous as vol
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import service

from .const import DOMAIN

SERVICE_LOAD_URL = "load_url"
SERVICE_SPEAK = "speak"
SERVICE_WAKE = "wake"
SERVICE_EVALUATE_JAVASCRIPT = "evaluate_javascript"


async def _async_clients(call: ServiceCall) -> list[Any]:
    """Resolve target WallPanel clients from device IDs."""
    device_ids: list[str] = call.data[ATTR_DEVICE_ID]
    return [
        service.async_get_device_and_config_entry(call.hass, DOMAIN, device_id)[
            1
        ].runtime_data.client
        for device_id in device_ids
    ]


async def _async_load_url(call: ServiceCall) -> None:
    """Load a URL on selected WallPanel devices."""
    for client in await _async_clients(call):
        await client.async_command(url=call.data["url"])


async def _async_speak(call: ServiceCall) -> None:
    """Speak text on selected WallPanel devices."""
    for client in await _async_clients(call):
        await client.async_command(speak=call.data["message"])


async def _async_wake(call: ServiceCall) -> None:
    """Wake selected WallPanel devices."""
    for client in await _async_clients(call):
        await client.async_command(wake=True, wakeTime=call.data["duration"])


async def _async_evaluate_javascript(call: ServiceCall) -> None:
    """Evaluate JavaScript in selected WallPanel dashboards."""
    for client in await _async_clients(call):
        await client.async_command(eval=call.data["javascript"])


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register WallPanel actions once."""
    if hass.services.has_service(DOMAIN, SERVICE_LOAD_URL):
        return

    device_schema = {vol.Required(ATTR_DEVICE_ID): cv.ensure_list}
    hass.services.async_register(
        DOMAIN,
        SERVICE_LOAD_URL,
        _async_load_url,
        schema=vol.Schema({**device_schema, vol.Required("url"): cv.url}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SPEAK,
        _async_speak,
        schema=vol.Schema({**device_schema, vol.Required("message"): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_WAKE,
        _async_wake,
        schema=vol.Schema(
            {
                **device_schema,
                vol.Optional("duration", default=180): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=86400)
                ),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_EVALUATE_JAVASCRIPT,
        _async_evaluate_javascript,
        schema=vol.Schema({**device_schema, vol.Required("javascript"): cv.string}),
    )
