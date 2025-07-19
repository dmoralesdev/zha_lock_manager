
from __future__ import annotations
import logging
from datetime import datetime, timedelta
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import storage, config_validation as cv
from homeassistant.helpers.event import async_track_point_in_time

from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    manager = ZhaLockManager(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager
    await manager.async_load()

    # Forward sensor platform (works on new and old HA)
    if hasattr(hass.config_entries, "async_forward_entry_setups"):
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    else:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, "sensor")
        )

    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

class ZhaLockManager:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.locks: list[str] = entry.data.get("locks", [])
        self.store = storage.Store(hass, STORAGE_VERSION, STORAGE_KEY)
        # codes structure: {lock_entity: {slot: {"code": str, "name": str | None, "expire": str | None}}}
        self.codes: dict[str, dict[int, dict]] = {}
        self._expiration_cleanup_remove = None

    async def async_load(self):
        data = await self.store.async_load()
        if data:
            self.codes = data
        self._schedule_cleanup()
        self._register_services_once()

    async def async_save(self):
        await self.store.async_save(self.codes)

    # ---------- Services ----------
    def _register_services_once(self):
        if self.hass.services.has_service(DOMAIN, "add_code"):
            return

        async def handle_add(call):
            lock_entity = call.data["lock_entity"]
            user_code = call.data["user_code"]
            name = call.data.get("name")
            slot = call.data.get("slot")
            expire = call.data.get("expire_at")
            expire_dt = datetime.fromisoformat(expire) if expire else None
            await self.async_add_code(lock_entity, user_code, name, slot, expire_dt)

        async def handle_delete(call):
            await self.async_delete_code(call.data["lock_entity"], call.data["slot"])

        async def handle_temp(call):
            lock_entity = call.data["lock_entity"]
            user_code = call.data["user_code"]
            name = call.data.get("name")
            slot = call.data.get("slot")
            minutes = call.data.get("duration_minutes", 60)
            expire_dt = datetime.utcnow() + timedelta(minutes=minutes)
            await self.async_add_code(lock_entity, user_code, name, slot, expire_dt)

        self.hass.services.async_register(
            DOMAIN,
            "add_code",
            handle_add,
            schema=vol.Schema(
                {
                    vol.Required("lock_entity"): cv.entity_id,
                    vol.Required("user_code"): cv.string,
                    vol.Optional("name"): cv.string,
                    vol.Optional("slot"): vol.Coerce(int),
                    vol.Optional("expire_at"): cv.string,
                }
            ),
        )

        self.hass.services.async_register(
            DOMAIN,
            "delete_code",
            handle_delete,
            schema=vol.Schema(
                {
                    vol.Required("lock_entity"): cv.entity_id,
                    vol.Required("slot"): vol.Coerce(int),
                }
            ),
        )

        self.hass.services.async_register(
            DOMAIN,
            "create_temp_code",
            handle_temp,
            schema=vol.Schema(
                {
                    vol.Required("lock_entity"): cv.entity_id,
                    vol.Required("user_code"): cv.string,
                    vol.Optional("name"): cv.string,
                    vol.Optional("slot"): vol.Coerce(int),
                    vol.Optional("duration_minutes", default=60): vol.Coerce(int),
                }
            ),
        )

    # ---------- Code management ----------
    async def async_add_code(self, lock_entity, user_code, name, slot, expire_dt):
        slot = slot or self._next_available_slot(lock_entity)

        await self.hass.services.async_call(
            "zha",
            "set_lock_user_code",
            {"entity_id": lock_entity, "code_slot": slot, "user_code": user_code},
            blocking=True,
        )

        self.codes.setdefault(lock_entity, {})[slot] = {
            "code": user_code,
            "name": name,
            "expire": expire_dt.isoformat() if expire_dt else None,
        }
        await self.async_save()
        self._schedule_cleanup()
        self._fire_update()

    async def async_delete_code(self, lock_entity, slot):
        await self.hass.services.async_call(
            "zha",
            "clear_lock_user_code",
            {"entity_id": lock_entity, "code_slot": slot},
            blocking=True,
        )
        if lock_entity in self.codes and slot in self.codes[lock_entity]:
            del self.codes[lock_entity][slot]
            await self.async_save()
            self._fire_update()

    def _next_available_slot(self, lock_entity):
        used = set(self.codes.get(lock_entity, {}).keys())
        slot = 1
        while slot in used:
            slot += 1
        return slot

    # ---------- Expiration ----------
    def _schedule_cleanup(self):
        if self._expiration_cleanup_remove:
            self._expiration_cleanup_remove()
            self._expiration_cleanup_remove = None

        soonest = None
        for lock, slots in self.codes.items():
            for slot, data in slots.items():
                exp = data.get("expire")
                if exp:
                    dt = datetime.fromisoformat(exp)
                    if dt < datetime.utcnow():
                        self.hass.async_create_task(self.async_delete_code(lock, slot))
                    else:
                        if soonest is None or dt < soonest:
                            soonest = dt

        if soonest:
            @callback
            def _run(_):
                self.hass.async_create_task(self._cleanup())

            self._expiration_cleanup_remove = async_track_point_in_time(
                self.hass, _run, soonest
            )

    async def _cleanup(self):
        await self.async_save()
        self._schedule_cleanup()

    def _fire_update(self):
        self.hass.bus.async_fire(f"{DOMAIN}_codes_updated")
