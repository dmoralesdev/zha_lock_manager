# ZHA Lock Manager

Manage keypad codes for Zigbee locks on Home Assistant through ZHA.  
Includes a simple side panel to view and edit codes, per lock settings, and an optional global Alarmo integration that disarms on successful keypad unlock.

<p align="center">
  <img src="custom_components\zha_lock_manager\frontend\zha_lock_manager.png" alt="Zigbee Locks side panel screenshot" width="646">
</p>

## Requirements

- Home Assistant 2025.8 or newer  
- ZHA integration with your lock entities available  
- HACS for easy install, or manual copy to `config/custom_components/zha_lock_manager`

## What this integration provides

- A Home Assistant integration entry with a config flow  
- A side panel named **Zigbee Locks** for daily code management  
- Support for multiple locks, selectable at install time and later from Options  
- Per lock settings managed in the panel:
  - Name
  - Max slots
  - Slot offset
- Code management actions per slot:
  - Set code
  - Enable code
  - Disable code
  - Clear code
- Optional global Alarmo hook:
  - On ZHA unlock from Keypad, the integration looks up the matching code and calls `alarm_control_panel.alarm_disarm` with that code

## How it works

### ZHA lock codes
- Codes are sent to the lock through ZHA services when you operate the panel using the below methods:
  - `zha.set_lock_user_code`
  - `zha.enable_lock_user_code`
  - `zha.disable_lock_user_code`
  - `zha.clear_lock_user_code`

### Alarmo integration
- The integration listens to `zha_event` and filters for:
  - `command: operation_event_notification`
  - `args.operation: Unlock`
  - `args.source: Keypad`
- When a keypad unlock occurs, it:
  - Finds the lock by IEEE
  - Applies the `slot_offset` to the reported `code_slot`
  - Decrypts the stored code for that slot
  - If Alarmo is enabled, calls `alarm_control_panel.alarm_disarm` (or your specified Alarmo entity name) with the code

## Installation

### HACS

1. In HACS, add this repository, then install **ZHA Lock Manager**.

[![Open your Home Assistant and add this integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=zha_lock_manager)

2. Restart Home Assistant.

### Manual

1. Copy `custom_components/zha_lock_manager` into your HA `config/custom_components` folder.
2. Restart Home Assistant.

## Setup

1. Go to **Settings**, **Devices and services**, **Integrations**.
2. Click **Add integration**, search for **ZHA Lock Manager**.
3. Select one or more ZHA lock entities to manage. You can add or remove locks later in Options.
4. Finish the flow. A **Zigbee Locks** sidebar panel will appear.

## Options

Open **Settings → Devices and services → ZHA Lock Manager → Configure**.

- **Locks**: pick which ZHA locks this integration manages. You can add or remove locks at any time.  
- **Enable Alarmo integration**: enable the global Alarmo hook.  
- **Alarmo entity_id**: set your `alarm_control_panel` entity.

Saving Options reloads the entry, updates the local store to match the selection, and refreshes the panel.

## The side panel

Open the **Zigbee Locks** panel from the sidebar.

- **Left column**: list of managed locks.  
- **Right column**:
  - Per lock metadata: **Name**, **Max slots**, **Slot offset**, **Save**.  
  - **Slots** table:
    - **Status** shows Empty, Enabled, or Disabled
    - **Set** prompts for a code and optional label, then programs the lock and stores the encrypted code
    - **Enable** is active only when the slot has a code and is currently Disabled
    - **Disable** is active only when the slot has a code and is currently Enabled
    - **Clear** removes the code on the lock and clears label and status in the store

### Per lock fields

- **Max slots**: how many numeric slots you want to manage in the panel. This does not change the lock hardware limit.  
- **Slot offset**: offset to apply when talking to the lock. Set this if your lock reports a `code_slot` that is shifted from the numbers you prefer to see in the UI.

## Data storage and security

- Codes are stored encrypted using a Fernet key that is generated on first load and saved in HA storage.  
- Encryption and data files are under `.storage` with private access enabled.  
- Removing a code from a slot clears the encrypted token, sets the slot to Disabled, and clears the label.  
- Removing the integration wipes all stored data and the encryption key, and removes the panel.

## Uninstall behavior

- Deleting the integration entry removes the sidebar panel and unsubscribes event listeners.  
- Stored lock data and the encryption key are deleted.  
- Reinstalling starts with an empty list of locks.

## Troubleshooting

- **Alarmo does not disarm on keypad unlock**  
  - Confirm the code exists in the manager for that slot, and that `slot_offset` is correct.  
  - Confirm **Enable Alarmo integration** is checked in Options and the `alarm_control_panel` entity is valid.  
  - The disarm hook only fires for `source: Keypad`.

## Known limitations

- The panel does not pull existing codes from the lock at install time. It manages codes that you set through the panel.  
- Some lock models enforce timing or rate limits on code changes. If a service call fails, retry after a short delay.  
- Max slots is a UI limit. Your lock may support fewer or more slots. Use a value that matches your hardware.

## Contributing

Bug reports and pull requests are welcome.  
Please include your Home Assistant version, a description of the lock model, and clear steps to reproduce.

## License
MIT
