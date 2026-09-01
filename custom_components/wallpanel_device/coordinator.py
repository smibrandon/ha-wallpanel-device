"""Coordinator and MQTT hub for WallPanel Device."""

from __future__ import annotations

import json
from typing import Any

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import WallPanelApiClient, WallPanelApiError
from .const import (
    CONF_MQTT_BASE_TOPIC,
    DEFAULT_SCAN_INTERVAL,
    LOGGER,
    SIGNAL_MQTT_UPDATE,
    SIGNAL_NEW_MQTT_SENSOR,
)


class WallPanelCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll WallPanel's HTTP state endpoint."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: WallPanelApiClient,
    ) -> None:
        """Initialize the coordinator."""
        self.client = client
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=DEFAULT_SCAN_INTERVAL,
            always_update=False,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the latest WallPanel state."""
        try:
            return await self.client.async_get_state()
        except WallPanelApiError as err:
            raise UpdateFailed(str(err)) from err


class WallPanelMqttHub:
    """Subscribe to WallPanel's MQTT sensor feed."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the MQTT hub."""
        self.hass = hass
        self.entry = entry
        self.base_topic = entry.data[CONF_MQTT_BASE_TOPIC].rstrip("/") + "/"
        self.connected: bool | None = None
        self.data: dict[str, dict[str, Any]] = {}
        self._unsubscribers: list[CALLBACK_TYPE] = []

    @property
    def signal_update(self) -> str:
        """Return this entry's update dispatcher signal."""
        return f"{SIGNAL_MQTT_UPDATE}_{self.entry.entry_id}"

    @property
    def signal_new_sensor(self) -> str:
        """Return this entry's new-sensor dispatcher signal."""
        return f"{SIGNAL_NEW_MQTT_SENSOR}_{self.entry.entry_id}"

    async def async_start(self) -> None:
        """Start MQTT subscriptions."""
        self._unsubscribers.extend(
            [
                await mqtt.async_subscribe(
                    self.hass,
                    f"{self.base_topic}connection",
                    self._async_connection_message,
                    qos=0,
                ),
                await mqtt.async_subscribe(
                    self.hass,
                    f"{self.base_topic}sensor/#",
                    self._async_sensor_message,
                    qos=0,
                ),
            ]
        )

    @callback
    def _async_connection_message(self, message: mqtt.ReceiveMessage) -> None:
        """Handle WallPanel availability."""
        self.connected = str(message.payload).lower() == "online"
        async_dispatcher_send(self.hass, self.signal_update)

    @callback
    def _async_sensor_message(self, message: mqtt.ReceiveMessage) -> None:
        """Handle a WallPanel sensor payload."""
        sensor_type = str(message.topic).removeprefix(f"{self.base_topic}sensor/")
        if not sensor_type or "/" in sensor_type:
            return
        try:
            payload = json.loads(message.payload)
        except (TypeError, ValueError):
            LOGGER.warning("Ignoring invalid JSON from MQTT topic %s", message.topic)
            return
        if not isinstance(payload, dict):
            return

        is_new = sensor_type not in self.data
        self.data[sensor_type] = payload
        if is_new:
            async_dispatcher_send(self.hass, self.signal_new_sensor, sensor_type)
        async_dispatcher_send(self.hass, self.signal_update)

    async def async_stop(self) -> None:
        """Stop MQTT subscriptions."""
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()

    async def async_remove_native_discovery(self, client_id: str) -> None:
        """Clear WallPanel's retained built-in MQTT discovery definitions."""
        topics = [
            f"homeassistant/sensor/{client_id}/battery/config",
            f"homeassistant/binary_sensor/{client_id}/usbPlugged/config",
            f"homeassistant/binary_sensor/{client_id}/acPlugged/config",
            f"homeassistant/binary_sensor/{client_id}/charging/config",
            f"homeassistant/sensor/{client_id}/temperature/config",
            f"homeassistant/sensor/{client_id}/light/config",
            f"homeassistant/sensor/{client_id}/magneticField/config",
            f"homeassistant/sensor/{client_id}/pressure/config",
            f"homeassistant/sensor/{client_id}/humidity/config",
            f"homeassistant/binary_sensor/{client_id}/face/config",
            f"homeassistant/binary_sensor/{client_id}/motion/config",
            f"homeassistant/tag/{client_id}/qr/config",
        ]
        for topic in topics:
            await mqtt.async_publish(self.hass, topic, "", qos=0, retain=True)


class WallPanelRuntimeData:
    """Runtime objects for one WallPanel config entry."""

    def __init__(
        self,
        client: WallPanelApiClient,
        coordinator: WallPanelCoordinator,
        mqtt_hub: WallPanelMqttHub,
    ) -> None:
        """Initialize runtime data."""
        self.client = client
        self.coordinator = coordinator
        self.mqtt_hub = mqtt_hub


type WallPanelConfigEntry = ConfigEntry[WallPanelRuntimeData]
