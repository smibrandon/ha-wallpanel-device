"""Binary sensors for WallPanel Device."""

from typing import override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_MQTT_CLIENT_ID
from .coordinator import WallPanelConfigEntry, WallPanelMqttHub
from .entity import WallPanelEntity, WallPanelMqttEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WallPanelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up WallPanel binary sensors."""
    runtime = entry.runtime_data
    hub = runtime.mqtt_hub
    async_add_entities(
        [
            WallPanelHttpBinarySensor(runtime.coordinator, "screenOn"),
            WallPanelHttpBinarySensor(runtime.coordinator, "camera"),
            WallPanelMqttConnectionSensor(runtime.coordinator, hub),
            WallPanelBatteryBinarySensor(runtime.coordinator, hub, "charging"),
            WallPanelBatteryBinarySensor(runtime.coordinator, hub, "acPlugged"),
            WallPanelBatteryBinarySensor(runtime.coordinator, hub, "usbPlugged"),
        ]
    )
    added: set[str] = set()

    @callback
    def add_detection_sensor(sensor_type: str) -> None:
        if sensor_type not in {"motion", "face"} or sensor_type in added:
            return
        added.add(sensor_type)
        async_add_entities(
            [WallPanelDetectionBinarySensor(runtime.coordinator, hub, sensor_type)]
        )

    for sensor_type in hub.data:
        add_detection_sensor(sensor_type)
    entry.async_on_unload(
        async_dispatcher_connect(hass, hub.signal_new_sensor, add_detection_sensor)
    )


class WallPanelHttpBinarySensor(WallPanelEntity, BinarySensorEntity):
    """A binary state exposed through WallPanel's HTTP API."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, key: str) -> None:
        """Initialize an HTTP binary sensor."""
        super().__init__(coordinator)
        client_id = coordinator.config_entry.data[CONF_MQTT_CLIENT_ID]
        self.key = key
        self._attr_unique_id = f"{client_id}_{key}"
        self._attr_translation_key = (
            "screen_on" if key == "screenOn" else "camera_enabled"
        )
        if key == "camera":
            self._attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    @override
    def is_on(self) -> bool | None:
        """Return current state."""
        value = self.coordinator.data.get(self.key)
        return bool(value) if value is not None else None


class WallPanelBatteryBinarySensor(WallPanelMqttEntity, BinarySensorEntity):
    """A power flag from WallPanel's battery payload."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, hub: WallPanelMqttHub, key: str) -> None:
        """Initialize a battery binary sensor."""
        super().__init__(coordinator, hub)
        client_id = coordinator.config_entry.data[CONF_MQTT_CLIENT_ID]
        self.key = key
        self._attr_unique_id = f"{client_id}_{key}"
        details = {
            "charging": (
                "charging",
                BinarySensorDeviceClass.BATTERY_CHARGING,
            ),
            "acPlugged": ("ac_plugged", BinarySensorDeviceClass.POWER),
            "usbPlugged": ("usb_plugged", BinarySensorDeviceClass.PLUG),
        }
        self._attr_translation_key, self._attr_device_class = details[key]

    @property
    @override
    def is_on(self) -> bool | None:
        """Return the latest power flag."""
        value = self.mqtt_hub.data.get("battery", {}).get(self.key)
        return bool(value) if value is not None else None

    @property
    @override
    def available(self) -> bool:
        """Return sensor availability."""
        return self.mqtt_hub.connected is not False and "battery" in self.mqtt_hub.data


class WallPanelMqttConnectionSensor(WallPanelMqttEntity, BinarySensorEntity):
    """WallPanel MQTT connection status."""

    _attr_translation_key = "mqtt_connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, hub: WallPanelMqttHub) -> None:
        """Initialize MQTT connection sensor."""
        super().__init__(coordinator, hub)
        client_id = coordinator.config_entry.data[CONF_MQTT_CLIENT_ID]
        self._attr_unique_id = f"{client_id}_mqtt_connected"

    @property
    @override
    def is_on(self) -> bool | None:
        """Return WallPanel MQTT connection state."""
        return self.mqtt_hub.connected

    @property
    @override
    def available(self) -> bool:
        """Keep the diagnostic entity available to report disconnection."""
        return True


class WallPanelDetectionBinarySensor(WallPanelMqttEntity, BinarySensorEntity):
    """Motion or face detection from WallPanel."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, hub: WallPanelMqttHub, sensor_type: str) -> None:
        """Initialize a detection sensor."""
        super().__init__(coordinator, hub)
        client_id = coordinator.config_entry.data[CONF_MQTT_CLIENT_ID]
        self.sensor_type = sensor_type
        self._attr_unique_id = f"{client_id}_{sensor_type}"
        self._attr_translation_key = sensor_type
        self._attr_device_class = (
            BinarySensorDeviceClass.MOTION
            if sensor_type == "motion"
            else BinarySensorDeviceClass.OCCUPANCY
        )

    @property
    @override
    def is_on(self) -> bool | None:
        """Return latest detection state."""
        value = self.mqtt_hub.data.get(self.sensor_type, {}).get("value")
        return bool(value) if value is not None else None
