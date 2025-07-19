
from __future__ import annotations
from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    manager = hass.data[DOMAIN][entry.entry_id]
    sensors = [CodesSensor(manager, lock) for lock in manager.locks]
    async_add_entities(sensors)

    @callback
    def _refresh(event):
        for sensor in sensors:
            sensor.async_write_ha_state()

    entry.async_on_unload(
        hass.bus.async_listen(f"{DOMAIN}_codes_updated", _refresh)
    )

class CodesSensor(Entity):
    should_poll = False

    def __init__(self, manager, lock_entity):
        self._manager = manager
        self._lock_entity = lock_entity
        self._attr_name = f"{lock_entity} codes"
        self._attr_unique_id = f"{lock_entity.replace('.', '_')}_codes"

    @property
    def state(self):
        return len(self._manager.codes.get(self._lock_entity, {}))

    @property
    def extra_state_attributes(self):
        return self._manager.codes.get(self._lock_entity, {})
