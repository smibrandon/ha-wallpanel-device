# WallPanel Device for Home Assistant

`WallPanel Device` turns each tablet running the Android WallPanel app into one
complete Home Assistant device. It combines WallPanel's HTTP state/command API
with its MQTT sensor feed.

## Features

- Local HTTP polling for screen state, camera state, brightness, and current URL
- MQTT battery, charging, AC/USB power, and available hardware sensors
- MQTT motion and face detection when those WallPanel features are enabled
- Screen brightness control
- Reload, relaunch, clear-cache, open-settings, and wake buttons
- Audio URL and Home Assistant media-source playback
- Volume control and stop
- Text-to-speech notify entity
- Actions for loading URLs, speaking text, waking the screen, and evaluating
  JavaScript
- Optional MJPEG camera entity, disabled by default

## Requirements

- Home Assistant 2025.6 or newer
- Home Assistant MQTT integration and an MQTT broker
- WallPanel MQTT, Sensor Publishing, and REST API enabled
- A unique MQTT client ID and base topic for every tablet

## Installation

### HACS custom repository

1. Add this repository to HACS as an **Integration** custom repository.
2. Install **WallPanel Device**.
3. Restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration** and search for
   **WallPanel Device**.

### Manual

Copy `custom_components/wallpanel_device` into Home Assistant's
`/config/custom_components/` directory, then restart Home Assistant.

## WallPanel settings

Example for a tablet named Firewhite:

```text
MQTT Enabled: On
Base Topic: wallpanel/firewhite-livingrm/
Client ID: firewhite-livingrm
Enable Sensor Publishing: On
Publish Frequency: 60 seconds
REST API: On
HTTP Listening Port: 2971
```

Once WallPanel Device is installed and working, disable WallPanel's built-in
**Home Assistant Discovery** option. During setup, the integration can remove
WallPanel's retained built-in discovery definitions so the old MQTT device does
not remain alongside the complete integration device. Re-enabling WallPanel
discovery recreates those definitions.

## Camera

The camera entity is included but disabled by default. To use it:

1. Enable the camera and **MJPEG Camera Streaming** in WallPanel.
2. Enable the Camera entity from the Home Assistant entity registry.

The integration does not remotely turn the WallPanel camera off because the
WallPanel 0.9.6 implementation also stops its HTTP server when the camera is
stopped.

## Security

WallPanel's HTTP API has no authentication. Keep port `2971` restricted to your
trusted LAN and do not expose it through a public reverse proxy.

