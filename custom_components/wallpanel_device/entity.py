"""Base entity for WallPanel Device."""

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from yarl import URL

from .const import CONF_MQTT_CLIENT_ID, DOMAIN
from .coordinator import WallPanelCoordinator, WallPanelMqttHub


class WallPanelEntity(CoordinatorEntity[WallPanelCoordinator]):
    """Base WallPanel entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WallPanelCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        client_id = entry.data[CONF_MQTT_CLIENT_ID]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, client_id)},
            name=entry.title,
            manufacturer="WallPanel",
            model="Android tablet",
            sw_version="0.9.6 compatible",
            configuration_url=str(
                URL.build(
                    scheme="http",
                    host=coordinator.client.host,
                    port=coordinator.client.port,
                )
            ),
        )


class WallPanelMqttEntity(WallPanelEntity):
    """Base entity backed by WallPanel MQTT data."""

    def __init__(
        self, coordinator: WallPanelCoordinator, mqtt_hub: WallPanelMqttHub
    ) -> None:
        """Initialize an MQTT-backed entity."""
        super().__init__(coordinator)
        self.mqtt_hub = mqtt_hub

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT update dispatches."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self.mqtt_hub.signal_update, self._handle_mqtt_update
            )
        )

    @callback
    def _handle_mqtt_update(self) -> None:
        """Write newly received MQTT data to Home Assistant."""
        self.async_write_ha_state()
