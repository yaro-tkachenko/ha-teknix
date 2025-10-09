from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, CONF_SERIAL, CONF_MODEL, MODELS

class TeknixConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            serial = user_input[CONF_SERIAL].strip()
            await self.async_set_unique_id(serial)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=f"Teknix {user_input[CONF_MODEL]} ({serial})", data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_SERIAL): str,
            vol.Required(CONF_MODEL): vol.In(list(MODELS)),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return TeknixOptionsFlow(config_entry)

class TeknixOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        return self.async_create_entry(title="", data=user_input)