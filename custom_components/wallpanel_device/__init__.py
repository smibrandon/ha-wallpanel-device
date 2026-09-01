"""WallPanel Device integration."""

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import WallPanelApiClient
from .const import (
    CONF_MQTT_CLIENT_ID,
    CONF_REMOVE_NATIVE_DISCOVERY,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import (
    WallPanelConfigEntry,
    WallPanelCoordinator,
    WallPanelMqttHub,
    WallPanelRuntimeData,
)
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up WallPanel Device."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: WallPanelConfigEntry) -> bool:
    """Set up a WallPanel device from a config entry."""
    if not mqtt.mqtt_config_entry_enabled(hass):
        raise ConfigEntryNotReady("The Home Assistant MQTT integration is not ready")

    client = WallPanelApiClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
    )
    coordinator = WallPanelCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    mqtt_hub = WallPanelMqttHub(hass, entry)
    await mqtt_hub.async_start()
    entry.runtime_data = WallPanelRuntimeData(client, coordinator, mqtt_hub)

    if entry.data.get(CONF_REMOVE_NATIVE_DISCOVERY, False):
        await mqtt_hub.async_remove_native_discovery(entry.data[CONF_MQTT_CLIENT_ID])

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WallPanelConfigEntry) -> bool:
    """Unload a WallPanel config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.mqtt_hub.async_stop()
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload WallPanel after config-entry changes."""
    await hass.config_entries.async_reload(entry.entry_id)
