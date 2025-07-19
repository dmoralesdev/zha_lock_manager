# ZHA Lock Manager

Dynamic user code management for Zigbee smart locks in Home Assistant.

---

## Features

* Unlimited user code slots  
* Temporary codes that expire automatically  
* Automatic cleanup of expired codes  
* Lovelace card for one‑click code management  
  * Detects the locks you selected during the config flow  
  * Drop‑down selector when multiple locks are available  
* Local only, no cloud calls

---

## Prerequisites

* Home Assistant 2024.6.0 or newer  
* Zigbee lock paired through the ZHA integration  
* HACS 2.x installed

---

## Installation

### 1. Add the integration with HACS

1. Open **Settings → Devices & services → HACS**  
2. Click **Explore & Download Repositories**  
3. Search **ZHA Lock Manager** (repository type Integration)  
4. Click **Download**, then restart Home Assistant  
5. After restart, Home Assistant discovers ZHA Lock Manager automatically  
6. Follow the wizard and select the lock entities you want to manage

### 2. Install the Lovelace card

One HACS repository can be only one type, so the card file is not inside the Integration repo. Choose one method:

| Method | Keeps HACS updates | Steps |
|--------|-------------------|-------|
| Separate dashboard repo (recommended) | Yes | 1. Add the repo that contains `zha-lock-manager-card.js` as type Dashboard in HACS. 2. Download and restart Home Assistant. 3. HACS adds the resource entry automatically. |
| Manual copy | Copy again after each update | 1. Download `zha-lock-manager-card.js`. 2. Copy it to `config/www/`. 3. Open **Settings → Dashboards → Resources**, click **Add resource**, set URL to `/local/zha-lock-manager-card.js`, select JavaScript module, save, then hard refresh the browser. |

---

## Add the Lovelace card

Paste this YAML in the card editor:

    type: custom:zha-lock-manager-card
    # lock: lock.front_door    (optional, leave out to auto detect)

If you omit `lock`, the card lists the locks chosen in the config flow and shows a drop‑down when more than one lock is found.

---

## Services

| Service | Purpose |
|---------|---------|
| `zha_lock_manager.add_code` | Add or update a persistent user code |
| `zha_lock_manager.delete_code` | Remove a user code from a slot |
| `zha_lock_manager.create_temp_code` | Add a code that expires after the requested duration |

All services require `lock_entity`. Open **Developer Tools → Services** for full schemas.

---

## Troubleshooting

| Symptom | Cause and fix |
|---------|---------------|
| Unknown custom element | The dashboard resource is missing or cached. Confirm the resource URL, then hard refresh the browser (Ctrl plus F5). |
| Slot friendly_name row appears | Update to card version dated 2025‑07‑19 or newer. Older files did not filter non numeric attributes. |
| Service error referencing `lock.front_door` | The example entity ID was copied. Edit the card or service call to use your real lock entity, or leave `lock` out so the card auto detects it. |

---

## Manual install (no HACS)

1. Copy `custom_components/zha_lock_manager` into `config/custom_components/`  
2. Copy `zha-lock-manager-card.js` into `config/www/` and add it as a dashboard resource `/local/zha-lock-manager-card.js` (type module)  
3. Restart Home Assistant and add the integration via **Settings → Devices & services → Add integration**  
4. Follow the wizard to select your lock entities

---

## Contributing

Pull requests are welcome. Use commas, parentheses, and colons instead of typographic em dashes.
