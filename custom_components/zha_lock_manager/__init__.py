from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.components.frontend import async_remove_panel

from .const import (
    DOMAIN,
    CONF_LOCKS,
    CONF_ALARMO_ENABLED,
    CONF_ALARMO_ENTITY_ID,
    EVENT_ZHA,
    PANEL_URL_PATH,
)
from .storage import ZLMLocalStore
from .websocket import register_ws_handlers
from .panel import async_register_panel

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Load or reload the integration."""
    hass.data.setdefault(DOMAIN, {})

    store = ZLMLocalStore(hass)
    await store.async_load()
    hass.data[DOMAIN]["store"] = store
    hass.data[DOMAIN]["entry"] = entry

    # Seed and prune locks according to entry.data
    cfg_locks: list[dict[str, Any]] = entry.data.get(CONF_LOCKS, [])
    selected_ieees: set[str] = set()

    # Add or keep selected locks
    for item in cfg_locks:
        entity_id = item.get("entity_id")
        device_ieee = item.get("device_ieee")
        name = item.get("name")
        max_slots = int(item.get("max_slots", 30))
        slot_offset = int(item.get("slot_offset", 0))
        if not (entity_id and device_ieee and name):
            continue
        selected_ieees.add(device_ieee)

        # Create only if not present, do not overwrite existing per lock fields
        if device_ieee not in store.locks or store.locks.get(device_ieee) is None:
            from .storage import Lock as LockModel

            store.locks[device_ieee] = LockModel(
                name=name,
                entity_id=entity_id,
                device_ieee=device_ieee,
                max_slots=max_slots,
                slot_offset=slot_offset,
                slots={},
            )

    # Remove locks that were deselected in options, erase their data
    to_delete = [ieee for ieee in list(store.locks.keys()) if ieee not in selected_ieees]
    if to_delete:
        for ieee in to_delete:
            del store.locks[ieee]
        _LOGGER.debug("ZLM: Pruned removed locks from local store: %s", to_delete)

    # Persist any adds or removals
    await store.async_save()

    # Register WS API once. Handlers now read the store from hass.data each call.
    if not hass.data[DOMAIN].get("ws_registered"):
        register_ws_handlers(hass)
        hass.data[DOMAIN]["ws_registered"] = True

    # Register or refresh panel
    await async_register_panel(hass)

    # Listen for ZHA unlock events to optionally disarm Alarmo
    @callback
    def _zha_event_handler(event):
        data = event.data or {}
        try:
            device_ieee = data.get("device_ieee")
            command = data.get("command")
            args = data.get("args", {})
            source = args.get("source")
            operation = args.get("operation")
            code_slot = args.get("code_slot")
        except Exception:
            return

        if command != "operation_event_notification" or operation != "Unlock":
            return
        if source not in ("Keypad", "RF"):
            return
        if device_ieee not in store.locks:
            return

        lock = store.locks[device_ieee]
        slot = int(code_slot) if code_slot is not None else None
        if slot is None:
            return
        slot_with_offset = slot + int(lock.slot_offset)

        # Alarmo integration check
        alarmo_enabled = entry.options.get(CONF_ALARMO_ENABLED, False)
        alarmo_entity = entry.options.get(CONF_ALARMO_ENTITY_ID)
        if not alarmo_enabled or not alarmo_entity:
            return

        # Retrieve and decrypt code, if unavailable, do nothing
        code = store.get_plain_code(lock, slot_with_offset)
        if not code:
            _LOGGER.debug("ZLM: No stored code for %s slot %s", device_ieee, slot_with_offset)
            return

        _LOGGER.debug(
            "ZLM: Disarming Alarmo via code from slot %s for %s",
            slot_with_offset,
            device_ieee,
        )
        hass.create_task(
            hass.services.async_call(
                "alarm_control_panel",
                "alarm_disarm",
                {"entity_id": alarmo_entity, "code": code},
                blocking=False,
            )
        )

    # Store unsubscribe so we can cleanly unload
    unsub = hass.bus.async_listen(EVENT_ZHA, _zha_event_handler)
    hass.data[DOMAIN]["unsub_zha_event"] = unsub

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry, remove panel, unsubscribe events."""
    try:
        async_remove_panel(hass, PANEL_URL_PATH)
    except Exception:
        pass

    if (unsub := hass.data.get(DOMAIN, {}).pop("unsub_zha_event", None)):
        try:
            unsub()
        except Exception:
            pass

    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove entry, wipe local data, remove panel."""
    try:
        async_remove_panel(hass, PANEL_URL_PATH)
    except Exception:
        pass

    store: ZLMLocalStore | None = hass.data.get(DOMAIN, {}).get("store")
    if store is None:
        # If not loaded, instantiate a temporary store to wipe files
        store = ZLMLocalStore(hass)
        await store.async_load()
    await store.async_wipe()

    # Best effort: clear domain data
    hass.data.pop(DOMAIN, None)
