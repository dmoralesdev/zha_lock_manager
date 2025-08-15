from __future__ import annotations

from typing import Any, Dict, List

from homeassistant.core import HomeAssistant
from homeassistant.components import websocket_api

from .const import DOMAIN
from .storage import ZLMLocalStore, Lock, Slot


def _require_store(hass: HomeAssistant) -> ZLMLocalStore:
    store: ZLMLocalStore | None = hass.data.get(DOMAIN, {}).get("store")
    if store is None:
        raise websocket_api.ActiveConnectionError("Lock manager store is not loaded")
    return store


def _serialize_lock(lock: Lock) -> Dict[str, Any]:
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


@websocket_api.websocket_command({"type": "zlm/list_locks"})
@websocket_api.async_response
async def ws_list_locks(hass, connection, msg):
    store = _require_store(hass)
    payload: List[Dict[str, Any]] = [_serialize_lock(l) for l in store.locks.values()]
    connection.send_result(msg["id"], payload)


@websocket_api.websocket_command(
    {
        "type": "zlm/set_code",
        "device_ieee": str,
        "slot": int,
        "code": str,
        "label": str,
    }
)
@websocket_api.async_response
async def ws_set_code(hass, connection, msg):
    store = _require_store(hass)
    lock = store.get_lock(msg["device_ieee"])
    if not lock:
        connection.send_error(msg["id"], "not_found", "Unknown lock")
        return
    store.set_code(lock, int(msg["slot"]), msg["code"], msg.get("label", ""), True)
    await store.async_save()
    connection.send_result(msg["id"], True)


@websocket_api.websocket_command(
    {
        "type": "zlm/enable_code",
        "device_ieee": str,
        "slot": int,
    }
)
@websocket_api.async_response
async def ws_enable_code(hass, connection, msg):
    store = _require_store(hass)
    lock = store.get_lock(msg["device_ieee"])
    if not lock:
        connection.send_error(msg["id"], "not_found", "Unknown lock")
        return
    s = store.ensure_slot(lock, int(msg["slot"]))
    if not s.code_encrypted:
        connection.send_error(msg["id"], "invalid", "No code set in this slot")
        return
    s.enabled = True
    await store.async_save()
    connection.send_result(msg["id"], True)


@websocket_api.websocket_command(
    {
        "type": "zlm/disable_code",
        "device_ieee": str,
        "slot": int,
    }
)
@websocket_api.async_response
async def ws_disable_code(hass, connection, msg):
    store = _require_store(hass)
    lock = store.get_lock(msg["device_ieee"])
    if not lock:
        connection.send_error(msg["id"], "not_found", "Unknown lock")
        return
    s = store.ensure_slot(lock, int(msg["slot"]))
    if not s.code_encrypted:
        connection.send_error(msg["id"], "invalid", "No code set in this slot")
        return
    s.enabled = False
    await store.async_save()
    connection.send_result(msg["id"], True)


@websocket_api.websocket_command(
    {
        "type": "zlm/clear_code",
        "device_ieee": str,
        "slot": int,
    }
)
@websocket_api.async_response
async def ws_clear_code(hass, connection, msg):
    store = _require_store(hass)
    lock = store.get_lock(msg["device_ieee"])
    if not lock:
        connection.send_error(msg["id"], "not_found", "Unknown lock")
        return
    store.clear_code(lock, int(msg["slot"]))
    await store.async_save()
    connection.send_result(msg["id"], True)


@websocket_api.websocket_command(
    {
        "type": "zlm/save_lock_meta",
        "device_ieee": str,
        "name": str,
        "max_slots": int,
        "slot_offset": int,
    }
)
@websocket_api.async_response
async def ws_save_lock_meta(hass, connection, msg):
    store = _require_store(hass)
    lock = store.get_lock(msg["device_ieee"])
    if not lock:
        connection.send_error(msg["id"], "not_found", "Unknown lock")
        return
    lock.name = msg["name"]
    lock.max_slots = int(msg["max_slots"])
    lock.slot_offset = int(msg["slot_offset"])
    await store.async_save()
    connection.send_result(msg["id"], True)


def register_ws_handlers(hass: HomeAssistant) -> None:
    """Register websocket commands. Fetch store from hass.data on each call."""
    websocket_api.async_register_command(hass, ws_list_locks)
    websocket_api.async_register_command(hass, ws_set_code)
    websocket_api.async_register_command(hass, ws_enable_code)
    websocket_api.async_register_command(hass, ws_disable_code)
    websocket_api.async_register_command(hass, ws_clear_code)
    websocket_api.async_register_command(hass, ws_save_lock_meta)
