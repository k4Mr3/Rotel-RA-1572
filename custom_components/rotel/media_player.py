import asyncio
import logging
import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerEntityFeature
from homeassistant.const import STATE_OFF, STATE_ON
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Rotel Amplifier"
DEFAULT_PORT = 9590
DEFAULT_MAX_VOLUME = 96  # Default max volume (no limit)

CONF_HOST = "host"
CONF_PORT = "port"
CONF_NAME = "name"
CONF_MAX_VOLUME = "max_volume"

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_MAX_VOLUME, default=DEFAULT_MAX_VOLUME): vol.All(
        vol.Coerce(int), vol.Range(min=1, max=96)
    ),
})

AUDIO_SOURCES = {
    'cd': 'CD',
    'analog_cd': 'CD',  # Alternative format returned by Rotel for CD input
    'coax1': 'Coax 1',
    'coax2': 'Coax 2',
    'opt1': 'Optical 1',
    'opt2': 'Optical 2',
    'aux': 'Aux',
    'tuner': 'Tuner',
    'phono': 'Phono',
    'usb': 'USB',
    'bluetooth': 'Bluetooth',
    'bal_xlr': 'XLR',
    'pc_usb': 'PC USB',  # Rotel returns pc_usb, we send pcusb command
}


class RotelDevice(MediaPlayerEntity):
    """Representation of the Rotel amplifier."""

    def __init__(self, name, host, port, max_volume=96):
        """Initialize the amplifier."""
        self._name = name
        self._host = host
        self._port = port
        self._max_volume = max_volume  # Maximum allowed volume level
        self._state = STATE_OFF
        
        # Initialize all values as None/Unknown - will be populated from Rotel
        self._rotel_volume = None
        self._mute = None
        self._source = None
        self._freq = None
        self._bass = None
        self._treble = None
        self._balance = None
        self._bypass = None
        self._speaker_a = None
        self._speaker_b = None
        self._dimmer = None
        self._pcusb_class = None
        self._update_mode = None
        
        self._tcp_lock = asyncio.Lock()
        self._listener_task = None  # Reference to the listening task
        self._command_writer = None  # Persistent connection for commands
        self._command_reader = None

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
        # Convert Rotel level to HA percentage for display
        if self._rotel_volume is not None:
            return self._rotel_volume / 100
        return None  # Unknown until first update from Rotel

    @property
    def is_volume_muted(self):
        """Return whether the volume is muted."""
        return self._mute if self._mute is not None else False

    @property
    def source_list(self):
        """Return the list of available sources."""
        return list(AUDIO_SOURCES.values())

    @property
    def source(self):
        """Return the currently selected source."""
        if self._source is not None:
            return AUDIO_SOURCES.get(self._source, "Unknown")
        return "Unknown"

    @property
    def supported_features(self):
        """Return the supported features."""
        return (
            MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.NEXT_TRACK
            | MediaPlayerEntityFeature.PREVIOUS_TRACK
        )

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return {
            "bass": self._bass,
            "treble": self._treble,
            "balance": self._balance,
            "bypass": self._bypass,
            "speaker_a": self._speaker_a,
            "speaker_b": self._speaker_b,
            "dimmer": self._dimmer,
            "pcusb_class": self._pcusb_class,
            "update_mode": self._update_mode,
            "frequency": self._freq,
            "max_volume": self._max_volume,
        }

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

    async def async_toggle(self):
        """Toggle power state."""
        await self._send_command("power_toggle!")
        self._state = STATE_ON if self._state == STATE_OFF else STATE_OFF
        self.async_write_ha_state()

    async def async_set_volume_level(self, volume):
        """Set the volume level with max volume protection."""
        # Direct 1:1 mapping: HA 50% (0.5) -> Rotel 50
        rotel_level = round(volume * 100)
        
        # Check max volume limit - if exceeded, reject the change
        if rotel_level > self._max_volume:
            _LOGGER.warning("Volume %d exceeds max volume limit %d, ignoring request", 
                          rotel_level, self._max_volume)
            return  # Don't change volume, keep previous value
        
        await self._send_command(f"vol_{rotel_level:02d}!")
        self._rotel_volume = rotel_level
        self.async_write_ha_state()

    async def async_mute_volume(self, mute):
        """Mute or unmute volume."""
        if mute:
            await self._send_command("mute_on!")
        else:
            await self._send_command("mute_off!")
        self._mute = mute
        self.async_write_ha_state()

    async def async_media_play(self):
        """Send play command."""
        await self._send_command("play!")

    async def async_media_pause(self):
        """Send pause command."""
        await self._send_command("pause!")

    async def async_media_stop(self):
        """Send stop command."""
        await self._send_command("stop!")

    async def async_media_next_track(self):
        """Send next track command."""
        await self._send_command("trkf!")

    async def async_media_previous_track(self):
        """Send previous track command."""
        await self._send_command("trkb!")

    async def async_select_source(self, source):
        """Select input source."""
        _LOGGER.debug("Selecting source: %s", source)
        source_key = next((key for key, value in AUDIO_SOURCES.items() if value == source), None)
        if source_key:
            _LOGGER.debug("Found source key: %s for source: %s", source_key, source)
            # For PC USB, always use 'pcusb' command regardless of which key was found
            if source_key == 'pc_usb':
                command_key = 'pcusb'
            # For CD, always use 'cd' command regardless of which key was found
            elif source_key in ['cd', 'analog_cd']:
                command_key = 'cd'
            else:
                command_key = source_key
            
            _LOGGER.debug("Sending command: %s!", command_key)
            await self._send_command(f"{command_key}!")
            self._source = source_key  # Store the actual received format
            _LOGGER.debug("Source set to: %s (will display as: %s)", source_key, AUDIO_SOURCES.get(source_key, "Unknown"))
            self.async_write_ha_state()
        else:
            _LOGGER.warning("Unknown source selected: %s", source)
    # Additional control methods
    async def set_bass(self, level):
        """Set bass level (-10 to +10)."""
        if level == 0:
            await self._send_command("bass_000!")
        elif level > 0:
            await self._send_command(f"bass_+{level:02d}!")
        else:
            await self._send_command(f"bass_{level:03d}!")
        self._bass = level
        self.async_write_ha_state()

    async def bass_up(self):
        """Increase bass."""
        await self._send_command("bass_up!")

    async def bass_down(self):
        """Decrease bass."""
        await self._send_command("bass_down!")

    async def set_treble(self, level):
        """Set treble level (-10 to +10)."""
        if level == 0:
            await self._send_command("treble_000!")
        elif level > 0:
            await self._send_command(f"treble_+{level:02d}!")
        else:
            await self._send_command(f"treble_{level:03d}!")
        self._treble = level
        self.async_write_ha_state()

    async def treble_up(self):
        """Increase treble."""
        await self._send_command("treble_up!")

    async def treble_down(self):
        """Decrease treble."""
        await self._send_command("treble_down!")

    async def set_balance(self, level):
        """Set balance (-15 to +15)."""
        if level == 0:
            await self._send_command("balance_000!")
        elif level > 0:
            await self._send_command(f"balance_r{level:02d}!")
        else:
            await self._send_command(f"balance_l{abs(level):02d}!")
        self._balance = level
        self.async_write_ha_state()

    async def balance_left(self):
        """Balance left."""
        await self._send_command("balance_l!")

    async def balance_right(self):
        """Balance right."""
        await self._send_command("balance_r!")

    async def set_bypass(self, bypass):
        """Set tone bypass."""
        if bypass:
            await self._send_command("bypass_on!")
        else:
            await self._send_command("bypass_off!")
        self._bypass = bypass
        self.async_write_ha_state()

    async def toggle_speaker_a(self):
        """Toggle speaker A output."""
        await self._send_command("speaker_a!")

    async def toggle_speaker_b(self):
        """Toggle speaker B output."""
        await self._send_command("speaker_b!")

    async def set_speaker_a(self, enabled):
        """Set speaker A output."""
        if enabled:
            await self._send_command("speaker_a_on!")
        else:
            await self._send_command("speaker_a_off!")
        self._speaker_a = enabled
        self.async_write_ha_state()

    async def set_speaker_b(self, enabled):
        """Set speaker B output."""
        if enabled:
            await self._send_command("speaker_b_on!")
        else:
            await self._send_command("speaker_b_off!")
        self._speaker_b = enabled
        self.async_write_ha_state()

    async def set_dimmer(self, level):
        """Set display dimmer level (0-6)."""
        if level == 0:
            await self._send_command("dimmer_0!")
        else:
            await self._send_command(f"dimmer_{level}!")
        self._dimmer = level
        self.async_write_ha_state()

    async def toggle_dimmer(self):
        """Toggle display dimmer."""
        await self._send_command("dimmer!")

    async def set_pcusb_class(self, usb_class):
        """Set PC-USB Audio Class (1 or 2)."""
        if usb_class == "2":
            await self._send_command("pcusb_class_2!")
        else:
            await self._send_command("pcusb_class_1!")
        self._pcusb_class = usb_class
        self.async_write_ha_state()

    async def factory_reset(self):
        """Reset unit to factory defaults."""
        await self._send_command("factory_default_on!")

    async def set_rs232_update_mode(self, auto_mode):
        """Set RS232 update mode."""
        if auto_mode:
            await self._send_command("rs232_update_on!")
            self._update_mode = "auto"
        else:
            await self._send_command("rs232_update_off!")
            self._update_mode = "manual"
        self.async_write_ha_state()

    async def get_device_info(self):
        """Request device information from Rotel."""
        _LOGGER.info("Requesting device information from Rotel...")
        info_commands = [
            "version?",     # Firmware version
            "pc_version?",  # PC-USB version
            "model?",       # Model number
            "ip?",          # IP address
            "mac?",         # MAC address
            "discover?",    # Discovery info
        ]
        
        for cmd in info_commands:
            try:
                await self._send_command(cmd)
                await asyncio.sleep(0.2)
            except Exception as e:
                _LOGGER.warning("Failed to request %s: %s", cmd, e)

    async def get_current_status(self):
        """Refresh all current status values from Rotel."""
        _LOGGER.info("Refreshing current status from Rotel...")
        await self._initialize_state()

    async def _ensure_command_connection(self):
        """Ensure we have a working command connection."""
        if self._command_writer is None or self._command_writer.is_closing():
            try:
                self._command_reader, self._command_writer = await asyncio.wait_for(
                    asyncio.open_connection(self._host, self._port),
                    timeout=5.0
                )
                _LOGGER.debug("Established command connection to Rotel")
            except Exception as e:
                _LOGGER.error("Failed to establish command connection: %s", e)
                self._command_writer = None
                self._command_reader = None
                raise

    async def _send_command(self, command, retries=3):
        """Send a command to the amplifier with persistent connection."""
        _LOGGER.debug("Sending command to Rotel: %s", command)
        
        for attempt in range(retries):
            try:
                async with self._tcp_lock:
                    await self._ensure_command_connection()
                    
                    if self._command_writer is None:
                        raise ConnectionError("No command connection available")
                    
                    self._command_writer.write(command.encode())
                    await asyncio.wait_for(self._command_writer.drain(), timeout=2.0)
                    
                    _LOGGER.debug("Command %s sent successfully", command)
                    return  # Success, exit retry loop
                    
            except asyncio.TimeoutError:
                _LOGGER.warning("Timeout sending command %s (attempt %d/%d)", command, attempt + 1, retries)
                await self._close_command_connection()
            except (ConnectionError, OSError) as e:
                _LOGGER.warning("Connection error sending command %s (attempt %d/%d): %s", command, attempt + 1, retries, e)
                await self._close_command_connection()
            except Exception as e:
                _LOGGER.warning("Error sending command %s (attempt %d/%d): %s", command, attempt + 1, retries, e)
                await self._close_command_connection()
            
            # Wait before retry
            if attempt < retries - 1:
                wait_time = 0.2 * (attempt + 1)  # 0.2s, 0.4s, 0.6s
                await asyncio.sleep(wait_time)
        
        # All retries failed
        _LOGGER.error("Failed to send command %s after %d attempts", command, retries)

    async def _close_command_connection(self):
        """Close the command connection."""
        if self._command_writer and not self._command_writer.is_closing():
            try:
                self._command_writer.close()
                await self._command_writer.wait_closed()
            except Exception:
                pass  # Ignore errors when closing
        self._command_writer = None
        self._command_reader = None

    async def _listen_for_updates(self):
        """Listen for real-time updates from the amplifier."""
        _LOGGER.debug("Starting to listen for updates.")
        while True:
            try:
                reader, writer = await asyncio.open_connection(self._host, self._port)
                _LOGGER.debug("Established listener connection to Rotel")
                
                while True:
                    try:
                        data = await asyncio.wait_for(reader.read(1024), timeout=30.0)
                        if data:
                            self._process_update(data.decode().strip())
                        else:
                            # Connection closed by remote
                            _LOGGER.debug("Listener connection closed by remote")
                            break
                    except asyncio.TimeoutError:
                        # Send a ping to keep connection alive
                        continue
                    except asyncio.CancelledError:
                        _LOGGER.debug("Listening task was cancelled.")
                        raise
                    except Exception as e:
                        _LOGGER.warning("Error reading from listener connection: %s", e)
                        break
                        
                # Close connection
                if writer and not writer.is_closing():
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except Exception:
                        pass
                        
            except asyncio.CancelledError:
                _LOGGER.debug("Listening task was cancelled.")
                break
            except Exception as e:
                _LOGGER.error("Error in listener connection: %s", e)
                
            # Wait before reconnecting
            await asyncio.sleep(5.0)
            
        _LOGGER.debug("Listener task ended.")

    def _process_update(self, response):
        """Process an incoming update from the amplifier."""
        _LOGGER.debug("Received update from Rotel: %s", response)
        
        # Split by both $ and newlines to handle different response formats
        # First split by $, then by newlines
        temp_parts = response.split('$')
        parts = []
        for temp_part in temp_parts:
            parts.extend(temp_part.split('\n'))
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            _LOGGER.debug("Processing part: '%s'", part)
                
            # Only process parts that contain key=value pairs
            if '=' in part:
                try:
                    key, value = part.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    _LOGGER.debug("Processing: %s = %s", key, value)
                    
                    if key == "power":
                        self._state = STATE_ON if value == "on" else STATE_OFF
                    elif key == "source":
                        self._source = value
                        _LOGGER.debug("Source updated to: %s (mapped to: %s)", value, AUDIO_SOURCES.get(value, "Unknown"))
                    elif key == "freq":
                        self._freq = value
                    elif key == "volume":
                        try:
                            vol_int = int(value)
                            if 1 <= vol_int <= 96:  # Validate range
                                # Store actual Rotel volume level
                                self._rotel_volume = vol_int
                                _LOGGER.debug("Volume updated: Rotel=%d", vol_int)
                            else:
                                _LOGGER.warning("Volume value out of range: %s", vol_int)
                        except ValueError:
                            _LOGGER.warning("Invalid volume value: %s", value)
                    elif key == "mute":
                        self._mute = value == "on"
                        _LOGGER.debug("Mute updated to: %s", self._mute)
                    elif key == "bass":
                        # Parse bass value (e.g., "000", "+10", "-05")
                        try:
                            if value.startswith('+'):
                                self._bass = int(value[1:])
                            elif value.startswith('-'):
                                self._bass = -int(value[1:])
                            else:
                                self._bass = int(value)
                            _LOGGER.debug("Bass updated to: %d", self._bass)
                        except ValueError:
                            _LOGGER.warning("Invalid bass value: %s", value)
                    elif key == "treble":
                        # Parse treble value (e.g., "000", "+10", "-05")
                        try:
                            if value.startswith('+'):
                                self._treble = int(value[1:])
                            elif value.startswith('-'):
                                self._treble = -int(value[1:])
                            else:
                                self._treble = int(value)
                            _LOGGER.debug("Treble updated to: %d", self._treble)
                        except ValueError:
                            _LOGGER.warning("Invalid treble value: %s", value)
                    elif key == "balance":
                        # Parse balance value (e.g., "000", "L15", "R10")
                        try:
                            if value.startswith('L'):
                                self._balance = -int(value[1:])
                            elif value.startswith('R'):
                                self._balance = int(value[1:])
                            else:
                                self._balance = 0
                            _LOGGER.debug("Balance updated to: %d", self._balance)
                        except ValueError:
                            _LOGGER.warning("Invalid balance value: %s", value)
                    elif key == "bypass":
                        self._bypass = value == "on"
                        _LOGGER.debug("Bypass updated to: %s", self._bypass)
                    elif key == "speaker":
                        # Parse speaker output (e.g., "a", "b", "a_b", "off")
                        self._speaker_a = 'a' in value
                        self._speaker_b = 'b' in value
                        _LOGGER.debug("Speakers updated: A=%s, B=%s", self._speaker_a, self._speaker_b)
                    elif key == "dimmer":
                        try:
                            self._dimmer = int(value) if value.isdigit() else 0
                            _LOGGER.debug("Dimmer updated to: %d", self._dimmer)
                        except ValueError:
                            _LOGGER.warning("Invalid dimmer value: %s", value)
                            self._dimmer = 0
                    elif key == "pcusb_class":
                        self._pcusb_class = value
                        _LOGGER.debug("PC-USB class updated to: %s", self._pcusb_class)
                    elif key == "update_mode":
                        self._update_mode = value
                        _LOGGER.debug("Update mode updated to: %s", self._update_mode)
                    # Additional query response handlers
                    elif key == "version":
                        _LOGGER.info("Rotel firmware version: %s", value)
                    elif key == "pc_version":
                        _LOGGER.info("Rotel PC-USB version: %s", value)
                    elif key == "ipaddress":
                        _LOGGER.info("Rotel IP address: %s", value)
                    elif key == "mac":
                        _LOGGER.info("Rotel MAC address: %s", value)
                    elif key == "model":
                        _LOGGER.info("Rotel model: %s", value)
                    elif key == "discover":
                        _LOGGER.info("Rotel discovery info: %s", value)
                    else:
                        _LOGGER.debug("Unknown key: %s = %s", key, value)
                        
                except ValueError as e:
                    _LOGGER.warning("Error parsing update '%s': %s", part, e)
            else:
                # This is likely a standalone number (previous value), ignore it
                _LOGGER.debug("Ignoring standalone value: %s", part)

        # Notify Home Assistant about the state change
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Start listening for updates when added to Home Assistant."""
        self._listener_task = self.hass.loop.create_task(self._listen_for_updates())
        
        # Initialize state by requesting current status from Rotel
        await self._initialize_state()

    async def async_will_remove_from_hass(self):
        """Cancel the listening task when the entity is removed."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                _LOGGER.debug("Listener task cancelled successfully.")
            self._listener_task = None
        
        # Close command connection
        await self._close_command_connection()

    async def _initialize_state(self):
        """Initialize state by requesting current values from Rotel using query commands."""
        _LOGGER.info("Initializing Rotel state - querying current values...")
        
        # Wait a moment for the device to be ready
        await asyncio.sleep(2.0)
        
        try:
            # Use proper query commands that don't change state
            query_commands = [
                "power?",     # Request current power status
                "source?",    # Request current source
                "volume?",    # Request current volume
                "mute?",      # Request current mute status
                "bypass?",    # Request current tone bypass state
                "bass?",      # Request current bass level
                "treble?",    # Request current treble level
                "balance?",   # Request current balance setting
                "speaker?",   # Request current active speaker outputs
                "dimmer?",    # Request current front display dimmer level
                "pcusb?",     # Request current PC-USB class
                "freq?",      # Request current frequency for digital source
            ]
            
            _LOGGER.debug("Sending query commands to Rotel...")
            for cmd in query_commands:
                try:
                    await self._send_command(cmd)
                    await asyncio.sleep(0.3)  # Increased delay between queries
                except Exception as e:
                    _LOGGER.warning("Failed to send query %s: %s", cmd, e)
            
            # Wait longer for responses to be processed
            _LOGGER.debug("Waiting for Rotel responses...")
            await asyncio.sleep(5.0)  # Increased wait time for all responses
            
            # Log what we actually received from Rotel
            _LOGGER.info("Rotel initialization results:")
            _LOGGER.info("  Power: %s", "ON" if self._state == STATE_ON else "OFF")
            _LOGGER.info("  Source: %s (%s)", self._source, AUDIO_SOURCES.get(self._source, "Unknown") if self._source else "None")
            _LOGGER.info("  Volume: %s", self._rotel_volume)
            _LOGGER.info("  Mute: %s", self._mute)
            _LOGGER.info("  Bass: %s", self._bass)
            _LOGGER.info("  Treble: %s", self._treble)
            _LOGGER.info("  Balance: %s", self._balance)
            _LOGGER.info("  Bypass: %s", self._bypass)
            _LOGGER.info("  Speakers A/B: %s/%s", self._speaker_a, self._speaker_b)
            _LOGGER.info("  Dimmer: %s", self._dimmer)
            _LOGGER.info("  PC-USB Class: %s", self._pcusb_class)
            
        except Exception as e:
            _LOGGER.error("Failed to query Rotel state: %s", e)
        
        # Set safe defaults ONLY for values that weren't received and are critical
        if self._rotel_volume is None:
            _LOGGER.warning("No volume response from Rotel, using default")
            self._rotel_volume = 50
            
        # Don't set defaults for these - let them remain None if Rotel doesn't respond
        # This prevents overriding actual Rotel settings with arbitrary defaults
        if self._bass is None:
            _LOGGER.warning("No bass response from Rotel - will show as unknown until first update")
            
        if self._treble is None:
            _LOGGER.warning("No treble response from Rotel - will show as unknown until first update")
            
        if self._balance is None:
            _LOGGER.warning("No balance response from Rotel - will show as unknown until first update")
            
        if self._bypass is None:
            _LOGGER.warning("No bypass response from Rotel - will show as unknown until first update")
            
        if self._speaker_a is None or self._speaker_b is None:
            _LOGGER.warning("No speaker response from Rotel - will show as unknown until first update")
            
        if self._dimmer is None:
            _LOGGER.warning("No dimmer response from Rotel - will show as unknown until first update")
            
        if self._pcusb_class is None:
            _LOGGER.warning("No PC-USB response from Rotel - will show as unknown until first update")
            
        if self._mute is None:
            _LOGGER.warning("No mute response from Rotel, using default")
            self._mute = False
            
        if self._source is None:
            _LOGGER.warning("No source response from Rotel, using default")
            self._source = "cd"  # Default to CD source
            
        if self._update_mode is None:
            self._update_mode = "auto"
        
        # Update HA state with current values
        self.async_write_ha_state()
        _LOGGER.info("Rotel state initialization completed")


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Rotel platform."""
    from homeassistant.helpers import entity_platform
    
    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    max_volume = config.get(CONF_MAX_VOLUME)

    amplifier = RotelDevice(name, host, port, max_volume)
    async_add_entities([amplifier])
    
    # Register platform services
    platform = entity_platform.async_get_current_platform()
    
    platform.async_register_entity_service(
        "set_bass",
        {
            "level": vol.All(vol.Coerce(int), vol.Range(min=-10, max=10))
        },
        "set_bass"
    )
    
    platform.async_register_entity_service(
        "set_treble",
        {
            "level": vol.All(vol.Coerce(int), vol.Range(min=-10, max=10))
        },
        "set_treble"
    )
    
    platform.async_register_entity_service(
        "set_balance",
        {
            "level": vol.All(vol.Coerce(int), vol.Range(min=-15, max=15))
        },
        "set_balance"
    )
    
    platform.async_register_entity_service(
        "set_bypass",
        {
            "bypass": vol.Coerce(bool)
        },
        "set_bypass"
    )
    
    platform.async_register_entity_service(
        "set_speaker_a",
        {
            "enabled": vol.Coerce(bool)
        },
        "set_speaker_a"
    )
    
    platform.async_register_entity_service(
        "set_speaker_b",
        {
            "enabled": vol.Coerce(bool)
        },
        "set_speaker_b"
    )
    
    platform.async_register_entity_service(
        "set_dimmer",
        {
            "level": vol.All(vol.Coerce(int), vol.Range(min=0, max=6))
        },
        "set_dimmer"
    )
    
    platform.async_register_entity_service(
        "set_pcusb_class",
        {
            "usb_class": vol.In(["1", "2"])
        },
        "set_pcusb_class"
    )
    
    platform.async_register_entity_service(
        "set_rs232_update_mode",
        {
            "auto_mode": vol.Coerce(bool)
        },
        "set_rs232_update_mode"
    )
    
    # Register services without parameters
    platform.async_register_entity_service("toggle_speaker_a", {}, "toggle_speaker_a")
    platform.async_register_entity_service("toggle_speaker_b", {}, "toggle_speaker_b")
    platform.async_register_entity_service("toggle_dimmer", {}, "toggle_dimmer")
    platform.async_register_entity_service("bass_up", {}, "bass_up")
    platform.async_register_entity_service("bass_down", {}, "bass_down")
    platform.async_register_entity_service("treble_up", {}, "treble_up")
    platform.async_register_entity_service("treble_down", {}, "treble_down")
    platform.async_register_entity_service("balance_left", {}, "balance_left")
    platform.async_register_entity_service("balance_right", {}, "balance_right")
    platform.async_register_entity_service("factory_reset", {}, "factory_reset")
    platform.async_register_entity_service("get_device_info", {}, "get_device_info")
    platform.async_register_entity_service("get_current_status", {}, "get_current_status")