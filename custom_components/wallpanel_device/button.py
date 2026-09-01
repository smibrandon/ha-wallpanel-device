"""Buttons for WallPanel Device."""

from collections.abc import Mapping
from typing import Any, override

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_MQTT_CLIENT_ID
from .coordinator import WallPanelConfigEntry
from .entity import WallPanelEntity

BUTTON_COMMANDS: Mapping[str, dict[str, Any]] = {
    "reload": {"reload": True},
    "relaunch": {"relaunch": True},
    "clear_cache": {"clearCache": True},
    "open_settings": {"settings": True},
    "wake": {"wake": True, "wakeTime": 180},
    "release_wake": {"wake": False},
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WallPanelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up WallPanel buttons."""
    async_add_entities(
        WallPanelCommandButton(entry.runtime_data.coordinator, key, command)
        for key, command in BUTTON_COMMANDS.items()
    )


class WallPanelCommandButton(WallPanelEntity, ButtonEntity):
    """A button that sends a WallPanel API command."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, key: str, command: dict[str, Any]) -> None:
        """Initialize a command button."""
        super().__init__(coordinator)
        client_id = coordinator.config_entry.data[CONF_MQTT_CLIENT_ID]
        self.command = command
        self._attr_unique_id = f"{client_id}_{key}"
        self._attr_translation_key = key

    @override
    async def async_press(self) -> None:
        """Send the command."""
        await self.coordinator.client.async_command(**self.command)
        if any(key in self.command for key in ("relaunch", "reload", "wake")):
            await self.coordinator.async_request_refresh()
