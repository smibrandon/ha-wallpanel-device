"""Async HTTP client for WallPanel."""

import asyncio
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession
from yarl import URL


class WallPanelApiError(Exception):
    """Base WallPanel API error."""


class WallPanelConnectionError(WallPanelApiError):
    """WallPanel could not be reached."""


class WallPanelResponseError(WallPanelApiError):
    """WallPanel returned an invalid response."""


class WallPanelApiClient:
    """Client for WallPanel's REST API."""

    def __init__(self, session: ClientSession, host: str, port: int) -> None:
        """Initialize the client."""
        self._session = session
        self.host = host
        self.port = port
        self.base_url = URL.build(scheme="http", host=host, port=port)

    @property
    def state_url(self) -> URL:
        """Return the state endpoint URL."""
        return self.base_url / "api" / "state"

    @property
    def command_url(self) -> URL:
        """Return the command endpoint URL."""
        return self.base_url / "api" / "command"

    @property
    def camera_url(self) -> URL:
        """Return the MJPEG stream URL."""
        return self.base_url / "camera" / "stream"

    async def async_get_state(self) -> dict[str, Any]:
        """Fetch current WallPanel state."""
        try:
            async with asyncio.timeout(10):
                response = await self._session.get(self.state_url)
                response.raise_for_status()
                data = await response.json(content_type=None)
        except (ClientError, ClientResponseError, TimeoutError) as err:
            raise WallPanelConnectionError(str(err)) from err

        if not isinstance(data, dict):
            raise WallPanelResponseError("State response is not a JSON object")

        required = {"currentUrl", "screenOn", "camera", "brightness"}
        if not required.issubset(data):
            missing = ", ".join(sorted(required - data.keys()))
            raise WallPanelResponseError(f"State response is missing: {missing}")

        return data

    async def async_command(self, **command: Any) -> None:
        """Send one or more WallPanel commands."""
        try:
            async with asyncio.timeout(10):
                response = await self._session.post(self.command_url, json=command)
                response.raise_for_status()
                result = await response.json(content_type=None)
        except (ClientError, ClientResponseError, TimeoutError) as err:
            raise WallPanelConnectionError(str(err)) from err

        if not isinstance(result, dict) or result.get("result") is not True:
            raise WallPanelResponseError("WallPanel rejected the command")
