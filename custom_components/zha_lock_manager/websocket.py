from __future__ import annotations

from typing import Any, Dict, List

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.components import websocket_api

from .const import (
    DOMAIN,
    WS_LIST_LOCKS,
    WS_GET_LOCK,
    WS_SET_CODE,
    WS_ENABLE_CODE,
    WS_DISABLE_CODE,
    WS_CLEAR_CODE,
    WS_RENAME_CODE,
    WS_SAVE_LOCK_META,
)
from .storage import ZLMLocalStore


def _require_store(hass: HomeAssistant) -> ZLMLocalStore:
    store: ZLMLocalStore | None = hass.data.get(DOMAIN, {}).get("store")
    if store is None:
        raise websocket_api.ActiveConnectionError("Lock manager store is not loaded")
    return store


def _lock_to_dict(lock) -> dict:
    return {
        "name": lock.name,
        "entity_id": lock.entity_id,
        "device_ieee": lock.device_ieee,
        "max_slots": int(lock.max_slots),
        "slot_offset": int(lock.slot_offset),
        "slots": {
            str(s.slot): {
                "slot": s.slot,
                "label": s.label,
                "enabled": bool(s.enabled),
                "has_code": bool(s.code_encrypted),
            }
            for s in sorted(lock.slots.values(), key=lambda x: x.slot)
        },
    }


@websocket_api.websocket_command({vol.Required("type"): WS_LIST_LOCKS})
@websocket_api.async_response
async def ws_list_locks(hass, connection, msg):
    store = _require_store(hass)
    payload: List[Dict[str, Any]] = [_lock_to_dict(l) for l in store.locks.values()]
    connection.send_result(msg["id"], payload)


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_GET_LOCK,
        vol.Required("device_ieee"): str,
    }
)
@websocket_api.async_response
async def ws_get_lock(hass, connection, msg):
    store = _require_store(hass)
    lock = store.get_lock(msg["device_ieee"])
    if not lock:
        connection.send_error(msg["id"], "not_found", "Unknown lock")
        return
    connection.send_result(msg["id"], _lock_to_dict(lock))


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_SET_CODE,
        vol.Required("device_ieee"): str,
        vol.Required("slot"): int,
        vol.Required("code"): str,
        vol.Optional("label", default=""): str,
    }
)
@websocket_api.async_response
async def ws_set_code(hass, connection, msg):
    store = _require_store(hass)
    lock = store.get_lock(msg["device_ieee"])
    if not lock:
        connection.send_error(msg["id"], "not_found", "Unknown lock")
        return

    slot = int(msg["slot"]) + int(lock.slot_offset)
    code = msg["code"]
    label = msg.get("label", "")

    # Write to the lock through ZHA
    await hass.services.async_call(
        "zha",
        "set_lock_user_code",
        {"code_slot": slot, "user_code": code},
        target={"entity_id": lock.entity_id},
        blocking=True,
    )

    # Persist locally
    store.set_code(lock, slot, code, label=label, enabled=True)
    await store.async_save()
    connection.send_result(msg["id"], _lock_to_dict(lock))


@websocket_api.websocket_command(
    {vol.Required("type"): WS_ENABLE_CODE, vol.Required("device_ieee"): str, vol.Required("slot"): int}
)
@websocket_api.async_response
async def ws_enable_code(hass, connection, msg):
    store = _require_store(hass)
    lock = store.get_lock(msg["device_ieee"])
    if not lock:
        connection.send_error(msg["id"], "not_found", "Unknown lock")
        return

    slot = int(msg["slot"]) + int(lock.slot_offset)

    await hass.services.async_call(
        "zha",
        "enable_lock_user_code",
        {"code_slot": slot},
        target={"entity_id": lock.entity_id},
        blocking=True,
    )

    s = store.ensure_slot(lock, slot)
    s.enabled = True
    await store.async_save()
    connection.send_result(msg["id"], _lock_to_dict(lock))


@websocket_api.websocket_command(
    {vol.Required("type"): WS_DISABLE_CODE, vol.Required("device_ieee"): str, vol.Required("slot"): int}
)
@websocket_api.async_response
async def ws_disable_code(hass, connection, msg):
    store = _require_store(hass)
    lock = store.get_lock(msg["device_ieee"])
    if not lock:
        connection.send_error(msg["id"], "not_found", "Unknown lock")
        return

    slot = int(msg["slot"]) + int(lock.slot_offset)

    await hass.services.async_call(
        "zha",
        "disable_lock_user_code",
        {"code_slot": slot},
        target={"entity_id": lock.entity_id},
        blocking=True,
    )

    s = store.ensure_slot(lock, slot)
    s.enabled = False
    await store.async_save()
    connection.send_result(msg["id"], _lock_to_dict(lock))


@websocket_api.websocket_command(
    {vol.Required("type"): WS_CLEAR_CODE, vol.Required("device_ieee"): str, vol.Required("slot"): int}
)
@websocket_api.async_response
async def ws_clear_code(hass, connection, msg):
    store = _require_store(hass)
    lock = store.get_lock(msg["device_ieee"])
    if not lock:
        connection.send_error(msg["id"], "not_found", "Unknown lock")
        return

    slot = int(msg["slot"]) + int(lock.slot_offset)

    await hass.services.async_call(
        "zha",
        "clear_lock_user_code",
        {"code_slot": slot},
        target={"entity_id": lock.entity_id},
        blocking=True,
    )

    store.clear_code(lock, slot)
    await store.async_save()
    connection.send_result(msg["id"], _lock_to_dict(lock))


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_RENAME_CODE,
        vol.Required("device_ieee"): str,
        vol.Required("slot"): int,
        vol.Required("label"): str,
    }
)
@websocket_api.async_response
async def ws_rename_code(hass, connection, msg):
    store = _require_store(hass)
    lock = store.get_lock(msg["device_ieee"])
    if not lock:
        connection.send_error(msg["id"], "not_found", "Unknown lock")
        return
    slot = int(msg["slot"]) + int(lock.slot_offset)
    s = store.ensure_slot(lock, slot)
    s.label = msg["label"]
    await store.async_save()
    connection.send_result(msg["id"], _lock_to_dict(lock))


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_SAVE_LOCK_META,
        vol.Required("device_ieee"): str,
        vol.Optional("name"): str,
        vol.Optional("max_slots"): int,
        vol.Optional("slot_offset"): int,
    }
)
@websocket_api.async_response
async def ws_save_lock_meta(hass, connection, msg):
    store = _require_store(hass)
    lock = store.get_lock(msg["device_ieee"])
    if not lock:
        connection.send_error(msg["id"], "not_found", "Unknown lock")
        return
    if "name" in msg:
        lock.name = msg["name"]
    if "max_slots" in msg:
        lock.max_slots = int(msg["max_slots"])
    if "slot_offset" in msg:
        lock.slot_offset = int(msg["slot_offset"])
    await store.async_save()
    connection.send_result(msg["id"], _lock_to_dict(lock))


def register_ws_handlers(hass: HomeAssistant) -> None:
    """Register websocket commands. Each handler fetches the live store."""
    websocket_api.async_register_command(hass, ws_list_locks)
    websocket_api.async_register_command(hass, ws_get_lock)
    websocket_api.async_register_command(hass, ws_set_code)
    websocket_api.async_register_command(hass, ws_enable_code)
    websocket_api.async_register_command(hass, ws_disable_code)
    websocket_api.async_register_command(hass, ws_clear_code)
    websocket_api.async_register_command(hass, ws_rename_code)
    websocket_api.async_register_command(hass, ws_save_lock_meta)
