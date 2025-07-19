
from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import DOMAIN

class ZhaLockManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # user_input["locks"] is list of entity_ids
            return self.async_create_entry(title="ZHA Lock Manager", data={"locks": user_input["locks"]})
        schema = vol.Schema(
            {
                vol.Required("locks"): selector.selector(
                    {
                        "entity": {
                            "domain": "lock",
                            "multiple": True
                        }
                    }
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
