import asyncio
import logging
import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    SUPPORT_TURN_ON, SUPPORT_TURN_OFF, SUPPORT_VOLUME_SET, SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_STEP, SUPPORT_SELECT_SOURCE
)
from homeassistant.const import STATE_OFF, STATE_ON
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Rotel Amplifier"
DEFAULT_PORT = 9590

CONF_HOST = "host"
CONF_PORT = "port"
CONF_NAME = "name"

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

AUDIO_SOURCES = {
    'phono': 'Phono',
    'cd': 'CD',
    'tuner': 'Tuner',
    'usb': 'USB',
    'opt1': 'Optical 1',
    'opt2': 'Optical 2',
    'coax1': 'Coax 1',
    'coax2': 'Coax 2',
    'bluetooth': 'Bluetooth',
    'pcusb': 'PC USB',
    'aux': 'Aux',
}


class RotelDevice(MediaPlayerEntity):
    """Representation of the Rotel amplifier."""

    def __init__(self, name, host, port):
        """Initialize the amplifier."""
        self._name = name
        self._host = host
        self._port = port
        self._state = STATE_OFF
        self._volume = 0.5
        self._mute = False
        self._source = None
        self._freq = None
        self._tcp_lock = asyncio.Lock()
        self._listener_task = None  # Reference to the listening task

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the player."""
        return self._state

    @property
    def volume_level(self):
        """Return the volume level (0-1)."""
        return self._volume

    @property
    def is_volume_muted(self):
        """Return whether the volume is muted."""
        return self._mute

    @property
    def source_list(self):
        """Return the list of available sources."""
        return list(AUDIO_SOURCES.values())

    @property
    def source(self):
        """Return the currently selected source."""
        return AUDIO_SOURCES.get(self._source, "Unknown")

    @property
    def supported_features(self):
        """Return the supported features."""
        return (
            SUPPORT_TURN_ON
            | SUPPORT_TURN_OFF
            | SUPPORT_VOLUME_SET
            | SUPPORT_VOLUME_MUTE
            | SUPPORT_VOLUME_STEP
            | SUPPORT_SELECT_SOURCE
        )

    async def async_turn_on(self):
        """Turn the amplifier on."""
        await self._send_command("power_on!")
        self._state = STATE_ON
        self.async_write_ha_state()

    async def async_turn_off(self):
        """Turn the amplifier off."""
        await self._send_command("power_off!")
        self._state = STATE_OFF
        self.async_write_ha_state()

    async def async_set_volume_level(self, volume):
        """Set the volume level."""
        await self._send_command(f"vol_{int(volume * 100)}!")
        self._volume = volume
        self.async_write_ha_state()

    async def async_select_source(self, source):
        """Select input source."""
        source_key = next((key for key, value in AUDIO_SOURCES.items() if value == source), None)
        if source_key:
            await self._send_command(f"{source_key}!")
            self._source = source_key
            self.async_write_ha_state()

    async def _send_command(self, command):
        """Send a command to the amplifier."""
        _LOGGER.debug("Sending command to Rotel: %s", command)
        try:
            async with self._tcp_lock:
                reader, writer = await asyncio.open_connection(self._host, self._port)
                writer.write(command.encode())
                await writer.drain()
                writer.close()
                await writer.wait_closed()
        except Exception as e:
            _LOGGER.error("Failed to send command %s: %s", command, e)

    async def _listen_for_updates(self):
        """Listen for real-time updates from the amplifier."""
        _LOGGER.debug("Starting to listen for updates.")
        try:
            reader, writer = await asyncio.open_connection(self._host, self._port)
            while True:
                try:
                    data = await reader.read(1024)  # Adjust buffer size if needed
                    if data:
                        self._process_update(data.decode().strip())
                except asyncio.CancelledError:
                    _LOGGER.debug("Listening task was cancelled.")
                    break
        except Exception as e:
            _LOGGER.error("Error in _listen_for_updates: %s", e)
        finally:
            _LOGGER.debug("Closing listening task.")

    def _process_update(self, response):
        """Process an incoming update from the amplifier."""
        _LOGGER.debug("Received update from Rotel: %s", response)
        updates = response.split('$')  # Split updates by `$`
        for update in updates:
            if "=" in update:
                key, value = update.split("=", 1)
                if key == "power":
                    self._state = STATE_ON if value == "on" else STATE_OFF
                elif key == "source":
                    self._source = value
                elif key == "freq":
                    self._freq = value
                elif key == "volume":
                    self._volume = int(value) / 100
                elif key == "mute":
                    self._mute = value == "on"

        # Notify Home Assistant about the state change
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Start listening for updates when added to Home Assistant."""
        self._listener_task = self.hass.loop.create_task(self._listen_for_updates())

    async def async_will_remove_from_hass(self):
        """Cancel the listening task when the entity is removed."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                _LOGGER.debug("Listener task cancelled successfully.")
            self._listener_task = None


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Rotel platform."""
    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)

    amplifier = RotelDevice(name, host, port)
    async_add_entities([amplifier])
