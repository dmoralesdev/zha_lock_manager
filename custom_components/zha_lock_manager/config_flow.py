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
    """Build the stored lock descriptor for a ZHA lock entity."""
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
        # The panel manages these per lock. Keep defaults here only for new locks.
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
        """Return the options flow handler."""
        return ZLMOptionsFlowHandler()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Initial setup: select ZHA locks and optional Alarmo support."""
        if user_input is not None:
            selected_entities: list[str] = user_input.get(CONF_LOCKS, [])
            locks: list[dict[str, Any]] = []
            for entity_id in selected_entities:
                lock_dict = _entity_to_lock_dict(self.hass, entity_id)
                if lock_dict:
                    locks.append(lock_dict)

            alarmo_enabled = bool(user_input.get(CONF_ALARMO_ENABLED, False))
            alarmo_entity = user_input.get(
                CONF_ALARMO_ENTITY_ID, "alarm_control_panel.alarmo"
            )

            return self.async_create_entry(
                title="ZHA Lock Manager",
                data={CONF_LOCKS: locks},
                options={
                    CONF_ALARMO_ENABLED: alarmo_enabled,
                    CONF_ALARMO_ENTITY_ID: alarmo_entity,
                },
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_LOCKS): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="lock",
                        integration="zha",
                        multiple=True,
                    )
                ),
                vol.Optional(CONF_ALARMO_ENABLED, default=False): bool,
                vol.Optional(
                    CONF_ALARMO_ENTITY_ID, default="alarm_control_panel.alarmo"
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="alarm_control_panel")
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_import(self, user_input: dict[str, Any] | None = None):
        """YAML import path, delegates to user step."""
        return await self.async_step_user(user_input)


class ZLMOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow: add or remove locks, set global Alarmo options."""

    def __init__(self) -> None:
        # self.config_entry is injected by Home Assistant
        pass

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        return await self.async_step_main(user_input)

    async def async_step_main(self, user_input: dict[str, Any] | None = None):
        # Current stored locks
        data = self.config_entry.data
        stored_locks: list[dict[str, Any]] = data.get(CONF_LOCKS, [])
        by_entity = {l["entity_id"]: l for l in stored_locks if "entity_id" in l}

        # Defaults for the form
        default_entities = list(by_entity.keys())
        alarmo_enabled_default = self.config_entry.options.get(CONF_ALARMO_ENABLED, False)
        alarmo_entity_default = self.config_entry.options.get(
            CONF_ALARMO_ENTITY_ID, "alarm_control_panel.alarmo"
        )

        fields: dict[Any, Any] = {
            # Let users add or remove managed locks in the future
            vol.Required(CONF_LOCKS, default=default_entities): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="lock",
                    integration="zha",
                    multiple=True,
                )
            ),
            # Global Alarmo settings, apply to all locks
            vol.Optional(CONF_ALARMO_ENABLED, default=alarmo_enabled_default): bool,
            vol.Optional(
                CONF_ALARMO_ENTITY_ID, default=alarmo_entity_default
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="alarm_control_panel")
            ),
        }

        if user_input is not None:
            # Merge selection into stored data:
            # keep existing per lock fields for locks that remain,
            # create defaults for brand new locks,
            # remove locks that were deselected.
            selected_entities: list[str] = user_input.get(CONF_LOCKS, [])
            new_locks: list[dict[str, Any]] = []
            for entity_id in selected_entities:
                if entity_id in by_entity:
                    new_locks.append(by_entity[entity_id])
                else:
                    lock_dict = _entity_to_lock_dict(self.hass, entity_id)
                    if lock_dict:
                        new_locks.append(lock_dict)

            # Update entry.data only with the lock list
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, CONF_LOCKS: new_locks},
            )

            # Persist options by returning them here
            result = self.async_create_entry(
                title="ZLM Options",
                data={
                    CONF_ALARMO_ENABLED: bool(user_input.get(CONF_ALARMO_ENABLED, False)),
                    CONF_ALARMO_ENTITY_ID: user_input.get(CONF_ALARMO_ENTITY_ID, ""),
                },
            )

            # Reload so the panel picks up lock additions or removals immediately
            self.hass.async_create_task(
                self.hass.config_entries.async_reload(self.config_entry.entry_id)
            )
            return result

        return self.async_show_form(step_id="main", data_schema=vol.Schema(fields))
