# Rotel-RA-1572
Home Assistant custom component

Overview
This custom integration allows you to control and monitor Rotel amplifiers via TCP/IP in Home Assistant. Designed to provide seamless interaction with your Rotel device, it not only supports standard control features like power, volume, mute, and source selection but also synchronizes with real-time state changes from the amplifier.

For example, if you use the Rotel remote control to turn the device on or change the input source, the integration will automatically detect and update the state in Home Assistant.

Important Note on Rotel Network Settings
To ensure that your Rotel amplifier can listen for commands and respond to Home Assistant even when in standby mode, you must configure the amplifier's settings appropriately.

Change "POWER OPTION" to "Quick"
Access the Rotel Amplifier Menu:

Use the amplifier's remote control or physical buttons to navigate to the settings menu.
Locate the "POWER OPTION" Setting:

In the settings menu, find the option labeled "POWER OPTION".
Set "POWER OPTION" to "Quick":

Change the value of "POWER OPTION" from the default setting to "Quick".

Instalation:

1. Create the custom_components Folder (if it doesn’t exist):

Inside the /config directory, check if there is a folder named custom_components.
If it doesn’t exist, create a new folder named custom_components.
Copy the rotel Folder:

Place the rotel folder (with all its contents) inside the custom_components folder.
The folder structure should look like this:
markdown
Copy code
/config/custom_components/rotel/
    ├── __init__.py
    ├── media_player.py
    ├── manifest.json

2. Add the Integration (configuration.yaml):

media_player:
  - platform: rotel
    host: 192.168.1.100
    port: 9590
    name: Rotel Amplifier

3. Verify the Integration:

After restarting, go to Settings → Devices & Services.
Check if the Rotel integration appears in the list.
Navigate to Developer Tools → States to see if the media_player.rotel_amplifier entity is available.
