"""Constants for the WallPanel Device integration."""

import logging
from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "wallpanel_device"
LOGGER = logging.getLogger(__package__)

CONF_DEVICE_NAME: Final = "device_name"
CONF_MQTT_BASE_TOPIC: Final = "mqtt_base_topic"
CONF_MQTT_CLIENT_ID: Final = "mqtt_client_id"
CONF_REMOVE_NATIVE_DISCOVERY: Final = "remove_native_discovery"

DEFAULT_PORT: Final = 2971
DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=30)

PLATFORMS: Final = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CAMERA,
    Platform.MEDIA_PLAYER,
    Platform.NOTIFY,
    Platform.NUMBER,
    Platform.SENSOR,
]

SIGNAL_MQTT_UPDATE: Final = f"{DOMAIN}_mqtt_update"
SIGNAL_NEW_MQTT_SENSOR: Final = f"{DOMAIN}_new_mqtt_sensor"

MQTT_NUMERIC_SENSORS: Final = {
    "temperature": ("temperature", "°C"),
    "light": ("illuminance", "lx"),
    "magneticField": (None, "µT"),
    "pressure": ("atmospheric_pressure", "hPa"),
    "humidity": ("humidity", "%"),
}
