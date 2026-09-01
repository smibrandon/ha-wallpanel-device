"""Number controls for WallPanel Device."""

from typing import override

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory
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
    """Set up WallPanel number entities."""
    async_add_entities([WallPanelBrightnessNumber(entry.runtime_data.coordinator)])


class WallPanelBrightnessNumber(WallPanelEntity, NumberEntity):
    """WallPanel screen brightness control."""

    _attr_translation_key = "screen_brightness"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 1
    _attr_native_max_value = 255
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator) -> None:
        """Initialize brightness control."""
        super().__init__(coordinator)
        client_id = coordinator.config_entry.data[CONF_MQTT_CLIENT_ID]
        self._attr_unique_id = f"{client_id}_brightness"

    @property
    @override
    def native_value(self) -> float | None:
        """Return current brightness."""
        value = self.coordinator.data.get("brightness")
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @override
    async def async_set_native_value(self, value: float) -> None:
        """Set screen brightness."""
        await self.coordinator.client.async_command(brightness=round(value))
        await self.coordinator.async_request_refresh()
