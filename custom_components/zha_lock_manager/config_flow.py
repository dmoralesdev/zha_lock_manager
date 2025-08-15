from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_LOCKS,
    CONF_ALARMO_ENABLED,
    CONF_ALARMO_ENTITY_ID,
    DEFAULT_SLOT_OFFSET,
)


def _entity_to_lock_dict(hass: HomeAssistant, entity_id: str) -> dict[str, Any] | None:
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    ent = ent_reg.async_get(entity_id)
    if not ent or ent.domain != "lock" or ent.platform != "zha":
        return None
    device = dev_reg.async_get(ent.device_id) if ent.device_id else None
    if not device:
        return None

    ieee: str | None = None
    for idt in device.identifiers:
        if idt[0] == "zha":
            ieee = idt[1]
            break

    return {
        "name": device.name or ent.original_name or ent.entity_id,
        "entity_id": ent.entity_id,
        "device_ieee": ieee or "",
        "max_slots": 30,
        "slot_offset": DEFAULT_SLOT_OFFSET,
    }


class ZLMCFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for ZHA Lock Manager."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create and return the options flow handler."""
        # Do not pass config_entry and do not assign self.config_entry in the handler.
        # Home Assistant injects self.config_entry automatically.
        # See dev docs: New options flow properties.
        return ZLMOptionsFlowHandler()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Pick ZHA lock entities to manage."""
        if user_input is not None:
            selected_entities: list[str] = user_input.get(CONF_LOCKS, [])
            locks: list[dict[str, Any]] = []
            for entity_id in selected_entities:
                lock_dict = _entity_to_lock_dict(self.hass, entity_id)
                if lock_dict:
                    locks.append(lock_dict)
            return self.async_create_entry(
                title="ZHA Lock Manager", data={CONF_LOCKS: locks}
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_LOCKS): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="lock", multiple=True)
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_import(self, user_input: dict[str, Any] | None = None):
        """Support YAML import by delegating to user step."""
        return await self.async_step_user(user_input)


class ZLMOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to edit lock metadata and optional Alarmo hookup."""

    def __init__(self) -> None:
        # Do not set self.config_entry here. It is provided by HA.
        pass

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        return await self.async_step_main(user_input)

    async def async_step_main(self, user_input: dict[str, Any] | None = None):
        data = self.config_entry.data
        locks: list[dict[str, Any]] = data.get(CONF_LOCKS, [])

        # Build per-lock editable fields
        fields: dict[Any, Any] = {}
        for idx, l in enumerate(locks):
            fields[vol.Optional(f"name_{idx}", default=l.get("name", ""))] = str
            fields[vol.Optional(f"entity_id_{idx}", default=l.get("entity_id", ""))] = str
            fields[vol.Optional(f"device_ieee_{idx}", default=l.get("device_ieee", ""))] = str
            fields[vol.Optional(f"max_slots_{idx}", default=l.get("max_slots", 30))] = int
            fields[
                vol.Optional(
                    f"slot_offset_{idx}", default=l.get("slot_offset", DEFAULT_SLOT_OFFSET)
                )
            ] = int

        # Global options for Alarmo
        fields[
            vol.Optional(
                CONF_ALARMO_ENABLED,
                default=self.config_entry.options.get(CONF_ALARMO_ENABLED, False),
            )
        ] = bool
        fields[
            vol.Optional(
                CONF_ALARMO_ENTITY_ID,
                default=self.config_entry.options.get(
                    CONF_ALARMO_ENTITY_ID, "alarm_control_panel.alarmo"
                ),
            )
        ] = str

        if user_input is not None:
            # Persist lock metadata back to entry.data
            new_locks: list[dict[str, Any]] = []
            idx = 0
            while f"name_{idx}" in user_input:
                new_locks.append(
                    {
                        "name": user_input.get(f"name_{idx}", ""),
                        "entity_id": user_input.get(f"entity_id_{idx}", ""),
                        "device_ieee": user_input.get(f"device_ieee_{idx}", ""),
                        "max_slots": int(user_input.get(f"max_slots_{idx}", 30)),
                        "slot_offset": int(
                            user_input.get(f"slot_offset_{idx}", DEFAULT_SLOT_OFFSET)
                        ),
                    }
                )
                idx += 1

            # Update entry data only
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, CONF_LOCKS: new_locks},
            )

            # Persist options by returning them from the options flow
            return self.async_create_entry(
                title="ZLM Options",
                data={
                    CONF_ALARMO_ENABLED: bool(user_input.get(CONF_ALARMO_ENABLED, False)),
                    CONF_ALARMO_ENTITY_ID: user_input.get(CONF_ALARMO_ENTITY_ID, ""),
                },
            )

        return self.async_show_form(step_id="main", data_schema=vol.Schema(fields))
