"""Sensors for WallPanel Device."""

from typing import Any, override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    LIGHT_LUX,
    PERCENTAGE,
    EntityCategory,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_MQTT_CLIENT_ID, MQTT_NUMERIC_SENSORS
from .coordinator import WallPanelConfigEntry, WallPanelMqttHub
from .entity import WallPanelEntity, WallPanelMqttEntity

SENSOR_DETAILS: dict[str, tuple[str, SensorDeviceClass | None, str | None]] = {
    "temperature": (
        "temperature",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
    "light": (
        "illuminance",
        SensorDeviceClass.ILLUMINANCE,
        LIGHT_LUX,
    ),
    "magneticField": (
        "magnetic_field",
        None,
        "µT",
    ),
    "pressure": (
        "pressure",
        SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        UnitOfPressure.HPA,
    ),
    "humidity": ("humidity", SensorDeviceClass.HUMIDITY, PERCENTAGE),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WallPanelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up WallPanel sensors."""
    runtime = entry.runtime_data
    hub = runtime.mqtt_hub
    added: set[str] = set()

    async_add_entities(
        [
            WallPanelCurrentUrlSensor(runtime.coordinator),
            WallPanelBatterySensor(runtime.coordinator, hub),
        ]
    )

    @callback
    def add_sensor(sensor_type: str) -> None:
        if sensor_type in added:
            return
        if sensor_type == "qrcode":
            added.add(sensor_type)
            async_add_entities([WallPanelQrCodeSensor(runtime.coordinator, hub)])
            return
        if sensor_type not in MQTT_NUMERIC_SENSORS:
            return
        added.add(sensor_type)
        async_add_entities(
            [WallPanelMqttNumericSensor(runtime.coordinator, hub, sensor_type)]
        )

    for sensor_type in hub.data:
        add_sensor(sensor_type)
    entry.async_on_unload(
        async_dispatcher_connect(hass, hub.signal_new_sensor, add_sensor)
    )


class WallPanelCurrentUrlSensor(WallPanelEntity, SensorEntity):
    """WallPanel current URL."""

    _attr_translation_key = "current_url"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        """Initialize current URL sensor."""
        super().__init__(coordinator)
        client_id = coordinator.config_entry.data[CONF_MQTT_CLIENT_ID]
        self._attr_unique_id = f"{client_id}_current_url"

    @property
    @override
    def native_value(self) -> str | None:
        """Return current URL, truncated to HA's state limit."""
        value = self.coordinator.data.get("currentUrl")
        return str(value)[:255] if value is not None else None

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the full URL when it is longer than the state."""
        value = self.coordinator.data.get("currentUrl")
        if value is None or len(str(value)) <= 255:
            return None
        return {"full_url": str(value)}


class WallPanelBatterySensor(WallPanelMqttEntity, SensorEntity):
    """WallPanel battery percentage."""

    _attr_translation_key = "battery_level"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, hub: WallPanelMqttHub) -> None:
        """Initialize battery sensor."""
        super().__init__(coordinator, hub)
        client_id = coordinator.config_entry.data[CONF_MQTT_CLIENT_ID]
        self._attr_unique_id = f"{client_id}_battery"

    @property
    @override
    def native_value(self) -> float | None:
        """Return battery percentage."""
        value = self.mqtt_hub.data.get("battery", {}).get("value")
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @property
    @override
    def available(self) -> bool:
        """Return MQTT battery availability."""
        return self.mqtt_hub.connected is not False and "battery" in self.mqtt_hub.data


class WallPanelMqttNumericSensor(WallPanelMqttEntity, SensorEntity):
    """An optional hardware sensor published by WallPanel."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, hub: WallPanelMqttHub, sensor_type: str) -> None:
        """Initialize a numeric MQTT sensor."""
        super().__init__(coordinator, hub)
        translation_key, device_class, unit = SENSOR_DETAILS[sensor_type]
        client_id = coordinator.config_entry.data[CONF_MQTT_CLIENT_ID]
        self.sensor_type = sensor_type
        self._attr_unique_id = f"{client_id}_{sensor_type}"
        self._attr_translation_key = translation_key
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit

    @property
    @override
    def native_value(self) -> float | None:
        """Return the latest sensor value."""
        value = self.mqtt_hub.data.get(self.sensor_type, {}).get("value")
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @property
    @override
    def available(self) -> bool:
        """Return sensor availability."""
        return (
            self.mqtt_hub.connected is not False
            and self.sensor_type in self.mqtt_hub.data
        )


class WallPanelQrCodeSensor(WallPanelMqttEntity, SensorEntity):
    """Last QR-code value seen by WallPanel."""

    _attr_translation_key = "qr_code"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, hub: WallPanelMqttHub) -> None:
        """Initialize QR-code sensor."""
        super().__init__(coordinator, hub)
        client_id = coordinator.config_entry.data[CONF_MQTT_CLIENT_ID]
        self._attr_unique_id = f"{client_id}_qrcode"

    @property
    @override
    def native_value(self) -> str | None:
        """Return the most recently scanned QR-code value."""
        value = self.mqtt_hub.data.get("qrcode", {}).get("value")
        return str(value)[:255] if value is not None else None
