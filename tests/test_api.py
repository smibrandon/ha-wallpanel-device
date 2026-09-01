"""Tests for the standalone WallPanel HTTP client."""

import asyncio
import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from aiohttp import web


def _load_api_module() -> ModuleType:
    """Load api.py without importing Home Assistant integration __init__."""
    path = (
        Path(__file__).parents[1] / "custom_components" / "wallpanel_device" / "api.py"
    )
    spec = importlib.util.spec_from_file_location("wallpanel_device_api", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


API = _load_api_module()


async def _with_server(state_payload, test_callback) -> None:
    """Run a test against a fake WallPanel HTTP server."""
    commands: list[dict] = []

    async def state_handler(request):
        return web.json_response(state_payload)

    async def command_handler(request):
        commands.append(await request.json())
        return web.json_response({"result": True})

    app = web.Application()
    app.router.add_get("/api/state", state_handler)
    app.router.add_post("/api/command", command_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    sockets = site._server.sockets
    port = sockets[0].getsockname()[1]

    try:
        await test_callback(port, commands)
    finally:
        await runner.cleanup()


def test_state_and_command_round_trip() -> None:
    """The client reads state and posts JSON commands."""

    async def scenario() -> None:
        payload = {
            "currentUrl": "https://example.test/dashboard/",
            "screenOn": True,
            "camera": False,
            "brightness": 255,
        }

        async def assertions(port, commands) -> None:
            from aiohttp import ClientSession

            async with ClientSession() as session:
                client = API.WallPanelApiClient(session, "127.0.0.1", port)
                assert await client.async_get_state() == payload
                await client.async_command(reload=True)
                assert commands == [{"reload": True}]
                assert str(client.camera_url).endswith("/camera/stream")

        await _with_server(payload, assertions)

    asyncio.run(scenario())


def test_invalid_state_is_rejected() -> None:
    """Missing standard state fields produce a response error."""

    async def scenario() -> None:
        async def assertions(port, commands) -> None:
            from aiohttp import ClientSession

            async with ClientSession() as session:
                client = API.WallPanelApiClient(session, "127.0.0.1", port)
                with pytest.raises(API.WallPanelResponseError):
                    await client.async_get_state()

        await _with_server({"screenOn": True}, assertions)

    asyncio.run(scenario())
