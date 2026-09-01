"""Static package tests."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "wallpanel_device"


def test_manifest() -> None:
    """Manifest declares an installable config-flow integration."""
    manifest = json.loads((INTEGRATION / "manifest.json").read_text())
    assert manifest["domain"] == "wallpanel_device"
    assert manifest["config_flow"] is True
    assert "mqtt" in manifest["dependencies"]
    assert manifest["version"]


def test_required_files_exist() -> None:
    """All declared platforms and UI metadata are packaged."""
    required = {
        "__init__.py",
        "binary_sensor.py",
        "button.py",
        "camera.py",
        "config_flow.py",
        "manifest.json",
        "media_player.py",
        "notify.py",
        "number.py",
        "sensor.py",
        "services.py",
        "services.yaml",
        "strings.json",
        "translations/en.json",
    }
    present = {
        str(path.relative_to(INTEGRATION))
        for path in INTEGRATION.rglob("*")
        if path.is_file()
    }
    assert required <= present
