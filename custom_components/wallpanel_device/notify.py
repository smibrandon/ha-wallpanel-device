"""Text-to-speech notifications for WallPanel Device."""

from typing import override

from homeassistant.components.notify import NotifyEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_MQTT_CLIENT_ID
from .coordinator import WallPanelConfigEntry
from .entity import WallPanelEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WallPanelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up WallPanel TTS notifications."""
    async_add_entities([WallPanelTtsNotify(entry.runtime_data.coordinator)])


class WallPanelTtsNotify(WallPanelEntity, NotifyEntity):
    """Send text to WallPanel's Android TTS engine."""

    _attr_translation_key = "text_to_speech"

    def __init__(self, coordinator) -> None:
        """Initialize TTS notifier."""
        WallPanelEntity.__init__(self, coordinator)
        NotifyEntity.__init__(self)
        client_id = coordinator.config_entry.data[CONF_MQTT_CLIENT_ID]
        self._attr_unique_id = f"{client_id}_tts"

    @override
    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Speak a message on the tablet."""
        await self.coordinator.client.async_command(speak=message)
