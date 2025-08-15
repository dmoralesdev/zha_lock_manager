from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import (
    DOMAIN,
    CONF_LOCKS,
    CONF_ALARMO_ENABLED,
    CONF_ALARMO_ENTITY_ID,
    EVENT_ZHA,
)
from .storage import ZLMLocalStore
from .websocket import register_ws_handlers
from .panel import async_register_panel

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Load or reload the integration.

    - Load local store
    - Seed new locks from entry.data
    - Prune locks removed in options
    - Register WS API and panel
    - Hook ZHA events for Alarmo
    """
    hass.data.setdefault(DOMAIN, {})

    store = ZLMLocalStore(hass)
    await store.async_load()
    hass.data[DOMAIN]["store"] = store
    hass.data[DOMAIN]["entry"] = entry

    # Locks selected in options
    cfg_locks: list[dict[str, Any]] = entry.data.get(CONF_LOCKS, [])
    selected_ieees: set[str] = set()
    dev_reg = dr.async_get(hass)

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

        # Create only if not present. Do not overwrite existing per lock fields.
        if device_ieee not in store.locks or store.locks.get(device_ieee) is None:
            from .storage import Lock as LockModel  # local import to avoid cycle

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

    # Register WS API
    register_ws_handlers(hass, store)

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

        _LOGGER.debug("ZLM: Disarming Alarmo via code from slot %s for %s", slot_with_offset, device_ieee)
        hass.create_task(
            hass.services.async_call(
                "alarm_control_panel",
                "alarm_disarm",
                {"entity_id": alarmo_entity, "code": code},
                blocking=False,
            )
        )

    hass.bus.async_listen(EVENT_ZHA, _zha_event_handler)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Nothing else to unload. Panel is stateless, WS handlers are re-registered on setup.
    return True
