from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from cryptography.fernet import Fernet, InvalidToken

from .const import (
    STORAGE_KEY,
    STORAGE_VERSION,
    KEY_STORAGE_KEY,
    KEY_STORAGE_VERSION,
)


@dataclass
class Slot:
    slot: int
    label: str = ""
    enabled: bool = True
    code_encrypted: Optional[str] = None  # base64 fernet token


@dataclass
class Lock:
    name: str
    entity_id: str
    device_ieee: str
    max_slots: int = 30
    slot_offset: int = 0
    slots: Dict[int, Slot] = field(default_factory=dict)


class Crypto:
    def __init__(self, key: bytes):
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()


class ZLMLocalStore:
    """Simple HA storage wrapper with encrypted codes and typed mapping."""

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY, private=True)
        self._key_store = Store(hass, KEY_STORAGE_VERSION, KEY_STORAGE_KEY, private=True)
        self.crypto: Optional[Crypto] = None
        self.locks: Dict[str, Lock] = {}

    async def async_load(self) -> None:
        # Load/generate key
        key_data = await self._key_store.async_load()
        if not key_data or "key" not in key_data:
            key = Fernet.generate_key()
            await self._key_store.async_save({"key": key.decode()})
        else:
            key = key_data["key"].encode()
        self.crypto = Crypto(key)

        data = await self._store.async_load()
        if not data:
            self.locks = {}
            return
        self.locks = {}
        for ieee, raw in data.get("locks", {}).items():
            slots: Dict[int, Slot] = {}
            for k, v in raw.get("slots", {}).items():
                slots[int(k)] = Slot(
                    slot=int(k),
                    label=v.get("label", ""),
                    enabled=v.get("enabled", True),
                    code_encrypted=v.get("code_encrypted"),
                )
            self.locks[ieee] = Lock(
                name=raw["name"],
                entity_id=raw["entity_id"],
                device_ieee=ieee,
                max_slots=raw.get("max_slots", 30),
                slot_offset=raw.get("slot_offset", 0),
                slots=slots,
            )

    async def async_save(self) -> None:
        data = {
            "locks": {
                ieee: {
                    "name": lock.name,
                    "entity_id": lock.entity_id,
                    "max_slots": lock.max_slots,
                    "slot_offset": lock.slot_offset,
                    "slots": {
                        str(s.slot): {
                            "label": s.label,
                            "enabled": s.enabled,
                            "code_encrypted": s.code_encrypted,
                        }
                        for s in lock.slots.values()
                    },
                }
                for ieee, lock in self.locks.items()
            }
        }
        await self._store.async_save(data)

    # Convenience helpers
    def get_lock(self, ieee: str) -> Optional[Lock]:
        return self.locks.get(ieee)

    def ensure_slot(self, lock: Lock, slot: int) -> Slot:
        if slot not in lock.slots:
            lock.slots[slot] = Slot(slot=slot)
        return lock.slots[slot]

    def set_code(self, lock: Lock, slot: int, code: str, label: str = "", enabled: bool = True) -> None:
        assert self.crypto
        s = self.ensure_slot(lock, slot)
        s.label = label
        s.enabled = enabled
        s.code_encrypted = self.crypto.encrypt(code)

    def clear_code(self, lock: Lock, slot: int) -> None:
        if slot in lock.slots:
            lock.slots[slot].code_encrypted = None
            lock.slots[slot].enabled = False

    def get_plain_code(self, lock: Lock, slot: int) -> Optional[str]:
        assert self.crypto
        s = lock.slots.get(slot)
        if not s or not s.code_encrypted:
            return None
        try:
            return self.crypto.decrypt(s.code_encrypted)
        except InvalidToken:
            return None