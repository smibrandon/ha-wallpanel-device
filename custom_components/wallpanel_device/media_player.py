"""Media player support for WallPanel Device."""

from typing import Any, override

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    BrowseMedia,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    async_process_play_media_url,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_MQTT_CLIENT_ID
from .coordinator import WallPanelConfigEntry
from .entity import WallPanelEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WallPanelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the WallPanel media player."""
    async_add_entities([WallPanelMediaPlayer(entry.runtime_data.coordinator)])


class WallPanelMediaPlayer(WallPanelEntity, MediaPlayerEntity):
    """Audio player exposed by WallPanel."""

    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.BROWSE_MEDIA
    )
    _attr_assumed_state = True

    def __init__(self, coordinator) -> None:
        """Initialize WallPanel media player."""
        super().__init__(coordinator)
        client_id = coordinator.config_entry.data[CONF_MQTT_CLIENT_ID]
        self._attr_unique_id = f"{client_id}_media_player"
        self._attr_state = MediaPlayerState.IDLE
        self._attr_volume_level = 0.5

    @override
    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs: Any
    ) -> None:
        """Play an audio URL or Home Assistant media-source item."""
        if media_source.is_media_source_id(media_id):
            play_item = await media_source.async_resolve_media(
                self.hass, media_id, self.entity_id
            )
            media_id = async_process_play_media_url(self.hass, play_item.url)
        else:
            media_id = async_process_play_media_url(self.hass, media_id)

        if media_type.startswith("audio/"):
            media_type = MediaType.MUSIC
        if media_type != MediaType.MUSIC:
            raise HomeAssistantError(f"Unsupported WallPanel media type: {media_type}")

        await self.coordinator.client.async_command(
            volume=round((self._attr_volume_level or 0.5) * 100),
            audio=media_id,
        )
        self._attr_media_content_type = MediaType.MUSIC
        self._attr_media_content_id = media_id
        self._attr_state = MediaPlayerState.PLAYING
        self.async_write_ha_state()

    @override
    async def async_media_stop(self) -> None:
        """Stop WallPanel audio playback."""
        await self.coordinator.client.async_command(audio="")
        self._attr_state = MediaPlayerState.IDLE
        self._attr_media_content_id = None
        self.async_write_ha_state()

    @override
    async def async_set_volume_level(self, volume: float) -> None:
        """Set WallPanel media volume."""
        volume = max(0.0, min(1.0, volume))
        await self.coordinator.client.async_command(volume=round(volume * 100))
        self._attr_volume_level = volume
        self.async_write_ha_state()

    @override
    async def async_browse_media(
        self,
        media_content_type: MediaType | str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """Browse Home Assistant audio media."""
        return await media_source.async_browse_media(
            self.hass,
            media_content_id,
            content_filter=lambda item: item.media_content_type.startswith("audio/"),
        )

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Preserve assumed playback state while updating availability."""
        self.async_write_ha_state()
