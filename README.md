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
  - It can respond to network queries for real-time state updates.

- If **"POWER OPTION"** is left at the default setting (e.g., **"Normal"**):
  - The network interface will shut down in standby mode.
  - Home Assistant will not be able to send commands or retrieve the device state.

---

## Installation

### 1. Create the `custom_components` Folder (if it doesn’t exist):

- Inside the `/config` directory, check if there is a folder named `custom_components`.
- If it doesn’t exist, create a new folder named `custom_components`.

### 2. Copy the `rotel` Folder:

- Place the `rotel` folder (with all its contents) inside the `custom_components` folder.


### 3. Add the Integration (`configuration.yaml`):

Add the following configuration to your `configuration.yaml` file:

```yaml
media_player:
- platform: rotel
  host: 192.168.1.100
  port: 9590
  name: Rotel Amplifier
```

4. Restart Home Assistant:


