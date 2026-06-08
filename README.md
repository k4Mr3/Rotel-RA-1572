# Rotel-RA-1572
**Home Assistant Custom Component**

## Overview

This custom integration allows you to control and monitor **Rotel amplifiers** via TCP/IP in Home Assistant. Designed to provide seamless interaction with your Rotel device, it not only supports standard control features like power, volume, mute, and source selection but also synchronizes with real-time state changes from the amplifier.

For example, if you use the Rotel remote control to turn the device on or change the input source, the integration will automatically detect and update the state in Home Assistant.

---

## Important Note on Rotel Network Settings

To ensure that your Rotel amplifier can listen for commands and respond to Home Assistant even when in **standby mode**, you must configure the amplifier's settings appropriately.

### Change **"POWER OPTION"** to **"Quick"**

1. **Access the Rotel Amplifier Menu:**

   Use the amplifier's remote control or physical buttons to navigate to the settings menu.

2. **Locate the "POWER OPTION" Setting:**

   In the settings menu, find the option labeled **"POWER OPTION"**.

3. **Set "POWER OPTION" to "Quick":**

   Change the value of **"POWER OPTION"** from the default setting to **"Quick"**.

### Why This Is Necessary

- When **"POWER OPTION"** is set to **"Quick"**, the amplifier keeps its network interface active even in standby mode. This ensures:
  - It can receive commands from Home Assistant.
  - It can respond to network queries for real-time state changes.

- If **"POWER OPTION"** is left at the default setting (e.g., **"Normal"**):
  - The network interface will shut down in standby mode.
  - Home Assistant will not be able to send commands or retrieve the device state.

---

## Installation

### Method 1: Via HACS (Recommended)

1. Open **HACS** in your Home Assistant dashboard.
2. Click the three dots in the top-right corner and select **Custom repositories**.
3. Paste the URL of this repository into the **Repository** field.
4. Select **Integration** as the category and click **Add**.
5. Find the **Rotel RA-1572** integration in the HACS list and click **Download**.
6. Restart Home Assistant.

### Method 2: Manual Installation

1. Navigate to your Home Assistant `/config` directory.
2. If it doesn't exist, create a folder named `custom_components`.
3. Create a new folder named `rotel` inside `custom_components`.
4. Copy all files from the `custom_components/rotel/` directory of this repository into that folder.
5. Restart Home Assistant.

---

## Configuration

Once the integration is installed, you need to configure it via your `configuration.yaml` file. Add the following block:

```yaml
media_player:
  - platform: rotel
    host: 192.168.1.100
    port: 9590
    name: Rotel Amplifier
    max_volume: 60  # Optional: Maximum volume limit (1-96, default: 96)
```

---

## Example Lovelace UI

This repository includes [rotel_clean_ui.yaml](examples/rotel_clean_ui.yaml) - a comprehensive example UI for Lovelace dashboards.

**⚠️ Important Note**: This UI is primarily designed for **debugging and testing purposes**. It includes all available controls and status displays, making it quite extensive and not optimized for daily use. Consider it a starting point to create your own customized interface.

**To use the example UI:**
1. Copy the contents of [rotel_clean_ui.yaml](examples/rotel_clean_ui.yaml)
2. Paste it into your Lovelace dashboard (raw configuration editor)
3. Customize it according to your needs

The example UI includes:
- All audio controls (bass, treble, balance)
- Speaker management
- Display settings
- System information
- Complete status overview

---

## New Features in Version 2.0.0

### Enhanced Audio Control
- **Bass/Treble Control**: Adjust bass and treble levels (-10 to +10)
- **Balance Control**: Left/right balance adjustment (-15 to +15)
- **Tone Bypass**: Enable/disable tone processing
- **Speaker Control**: Independent control of Speaker A and B outputs

### Display & Settings
- **Display Dimmer**: Adjust front panel brightness (0-6 levels)
- **PC-USB Class**: Switch between USB Audio Class 1.0 and 2.0
- **RS232 Update Mode**: Auto/manual status update control

### Safety Features
- **Maximum Volume Limit**: Set volume ceiling to protect hearing (configuration-only)
- **Query Commands**: Non-intrusive status polling using proper Rotel query commands
- **Connection Management**: Robust TCP connection handling with retry logic

### Source Mapping Fixes
- **PC USB Source**: Fixed mapping for `pc_usb` response format
- **CD Source**: Fixed mapping for `analog_cd` response format  
- **Volume Control**: Simplified 1:1 mapping (HA 50% = Rotel 50)

### Initialization Improvements
- **Respects Rotel Settings**: No longer overwrites amplifier settings with defaults
- **Extended Query Time**: Increased timeout for reliable state retrieval
- **Detailed Logging**: Comprehensive initialization status reporting

### Advanced Services
All features available through Home Assistant services:
- `rotel.set_bass`, `rotel.set_treble`, `rotel.set_balance`
- `rotel.toggle_speaker_a`, `rotel.toggle_speaker_b`
- `rotel.set_dimmer`, `rotel.set_bypass`
- `rotel.get_device_info`, `rotel.get_current_status`

### Configuration Parameters
```yaml
media_player:
- platform: rotel
  host: 192.168.1.100        # Required: Amplifier IP address
  port: 9590                 # Optional: TCP port (default: 9590)
  name: Rotel Amplifier      # Optional: Entity name
  max_volume: 60             # Optional: Max volume limit (1-96, default: 96)
```

---

## Supported Rotel Models

- **Rotel RA-1572** (tested)
- **Rotel RA-1572MKII** (should work)
- Other Rotel amplifiers with TCP/IP control using the same command protocol

---

## Troubleshooting

### Enable Debug Logging

Add to your `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.rotel: debug
```

### Common Issues

1. **"Connection refused"**: Check if POWER OPTION is set to "Quick"
2. **"Source shows as Unknown"**: Check logs for actual response format from your Rotel model
3. **"Settings reset on restart"**: Check initialization logs to see what values are received from Rotel

### Getting Help

Check the logs after enabling debug mode. The integration provides detailed information about:
- Connection status
- Commands sent and responses received
- Initialization process results
- Real-time state changes

---

## Contributing

Feel free to submit issues and enhancement requests. When reporting issues, please include:
- Your Rotel model
- Home Assistant version
- Debug logs showing the problem
- Steps to reproduce the issue

