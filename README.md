A lightweight Home Assistant custom integration to manage **Zigbee door lock user codes** using **ZHA** — with a built-in **sidebar panel** for UI management and an **optional Alarmo hook** to disarm when a valid keypad/RF code is used.

## Features

- Manage multiple Zigbee locks (ZHA) from a dedicated sidebar panel
- Add/enable/disable/clear codes via ZHA services
- Encrypted at rest using Fernet (cryptography)
- Local store of assigned slots & labels (acts as source of truth)
- Optional **Alarmo** integration: on unlock-by-code, look up the slot, decrypt the code, and call `alarm_control_panel.alarm_disarm`
- Per-lock **slot offset** to handle devices that report slot numbers off-by-one

## Requirements

- Home Assistant 2024.7+
- ZHA integration with at least one Zigbee lock entity
- (Optional) Alarmo integration and an alarm entity (e.g. `alarm_control_panel.alarmo`)

## Installation (via HACS)

1. In HACS → Integrations → **Custom repositories** → Add this repo URL as type **Integration**.
2. Install **ZHA Lock Manager**.
3. Restart Home Assistant.
4. Go to **Settings → Devices & services → Add Integration → ZHA Lock Manager**.
5. Select your ZHA lock(s).
6. Open the **Zigbee Locks** sidebar tab to manage codes.
7. (Optional) In **Integration Options**, enable *Alarmo integration* and set your `alarm_control_panel` entity.

## Notes & Limitations

- The integration assumes you manage codes **only** from this UI. Manual changes via Developer Tools or other automations won’t be seen.
- Some lock models report event **code_slot** shifted by 1; use *slot offset* in options to correct mapping.
- Codes are encrypted at rest (Fernet). The symmetric key is generated and stored privately under `.storage`.

## Uninstall

- Remove the integration from Settings → Devices & Services.
- Delete the HACS repository.

## License

MIT
