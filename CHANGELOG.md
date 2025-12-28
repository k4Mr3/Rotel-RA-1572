# Changelog

## Version 2.0.0 (2025-12-28)

###  New Features
- **Enhanced Audio Control**: Bass/Treble control (-10 to +10), Balance control (-15 to +15)
- **Speaker Management**: Independent control of Speaker A and B outputs
- **Display Control**: Adjustable front panel brightness (0-6 levels)
- **PC-USB Settings**: Switch between USB Audio Class 1.0 and 2.0
- **Tone Bypass**: Enable/disable tone processing
- **Device Information**: Get firmware version, model, IP, MAC address
- **Status Refresh**: Manual refresh of all current status values

###  Fixes
- **Source Mapping**: Fixed PC USB (`pc_usb`) and CD (`analog_cd`) source detection
- **Volume Control**: Simplified to 1:1 mapping (HA 50% = Rotel 50)
- **Initialization**: No longer overwrites Rotel settings with defaults
- **Connection Handling**: Improved TCP connection stability with retry logic
- **Response Parsing**: Better handling of different response formats

###  Safety Features
- **Maximum Volume Limit**: Configuration-only volume ceiling (1-96 range)
- **Query Commands**: Non-intrusive status polling using proper Rotel query commands
- **Extended Timeout**: Increased initialization timeout for reliable state retrieval

###  Documentation
- **Complete README**: Installation, configuration, troubleshooting guide
- **Extended Features**: Detailed service documentation with examples
- **Example UI**: Comprehensive Lovelace UI for debugging and testing
- **Debug Logging**: Detailed logging instructions for troubleshooting

###  Breaking Changes
- Removed runtime `set_max_volume` service (configuration-only for safety)
- Volume up/down services removed (use volume_set instead)

###  Home Assistant Compatibility
- **Minimum Version**: Home Assistant Core 2025.10+
- **Deprecated Constants**: Replaced `SUPPORT_*` with `MediaPlayerEntityFeature.*`

---

## Version 1.0.0 (Previous)

### Initial Features
- Basic media player functionality
- Power, volume, mute, source selection
- Real-time state synchronization
- TCP/IP communication with Rotel amplifiers

---

## Installation Requirements

- Home Assistant Core 2025.10 or later
- Rotel amplifier with TCP/IP control (tested on RA-1572)
- Network connection to amplifier
- Rotel "POWER OPTION" set to "Quick" for standby operation