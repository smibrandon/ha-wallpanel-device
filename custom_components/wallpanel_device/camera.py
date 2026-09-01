"""Optional MJPEG camera for WallPanel Device."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import override

import aiohttp
from aiohttp import web
from homeassistant.components.camera import Camera
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import (
    async_aiohttp_proxy_web,
    async_get_clientsession,
)
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_MQTT_CLIENT_ID
from .coordinator import WallPanelConfigEntry
from .entity import WallPanelEntity

TIMEOUT = 10


async def _async_extract_jpeg(stream: AsyncIterator[bytes]) -> bytes | None:
    """Extract the first JPEG from an MJPEG byte stream."""
    data = b""
    async for chunk in stream:
        data += chunk
        end = data.find(b"\xff\xd9")
        if end == -1:
            continue
        start = data.find(b"\xff\xd8")
        if start != -1:
            return data[start : end + 2]
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WallPanelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up optional WallPanel camera."""
    async_add_entities([WallPanelCamera(entry.runtime_data.coordinator)])


class WallPanelCamera(WallPanelEntity, Camera):
    """WallPanel MJPEG camera stream."""

    _attr_translation_key = "camera"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator) -> None:
        """Initialize WallPanel camera."""
        WallPanelEntity.__init__(self, coordinator)
        Camera.__init__(self)
        client_id = coordinator.config_entry.data[CONF_MQTT_CLIENT_ID]
        self._attr_unique_id = f"{client_id}_camera"

    @property
    @override
    def available(self) -> bool:
        """Return true when HTTP is reachable and WallPanel reports camera enabled."""
        return self.coordinator.available and bool(
            self.coordinator.data.get("camera", False)
        )

    @override
    async def stream_source(self) -> str:
        """Return WallPanel's MJPEG stream URL."""
        return str(self.coordinator.client.camera_url)

    @override
    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Extract a still frame from WallPanel's MJPEG stream."""
        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(TIMEOUT):
                async with session.get(self.coordinator.client.camera_url) as response:
                    response.raise_for_status()
                    return await _async_extract_jpeg(
                        response.content.iter_chunked(102400)
                    )
        except (aiohttp.ClientError, TimeoutError) as err:
            raise HomeAssistantError(f"Unable to read WallPanel camera: {err}") from err

    @override
    async def handle_async_mjpeg_stream(
        self, request: web.Request
    ) -> web.StreamResponse | None:
        """Proxy WallPanel's MJPEG stream through Home Assistant."""
        session = async_get_clientsession(self.hass)
        stream_coro = session.get(self.coordinator.client.camera_url)
        with suppress(aiohttp.ClientError, TimeoutError):
            return await async_aiohttp_proxy_web(self.hass, request, stream_coro)
        return None
