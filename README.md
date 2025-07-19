
# ZHA Lock Manager

Dynamic user code management for Zigbee smart locks in Home Assistant.

## Features

- Add, delete, and list lock user codes without fixed limits
- Create temporary codes that expire automatically
- Minimal Lovelace card for quick management

## Installation via HACS

1. In HACS, add this repository as a custom integration.
2. Install **ZHA Lock Manager** from the integrations tab.
3. Restart Home Assistant, then configure the integration.
4. In HACS, go to **Frontend** and install the **ZHA Lock Manager Card**.
5. Add the resource `/hacsfiles/zha_lock_manager/zha-lock-manager-card.js` to your Lovelace resources.

## Add the Lovelace Card

```yaml
type: custom:zha-lock-manager-card
lock: lock.front_door
```

Replace `lock.front_door` with your lock entity id.

## Services

- `zha_lock_manager.add_code`
- `zha_lock_manager.delete_code`
- `zha_lock_manager.create_temp_code`
