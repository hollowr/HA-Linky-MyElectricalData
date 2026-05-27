import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import DOMAIN, API_BASE, CONF_PDL, CONF_TOKEN

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_PDL): str,
    vol.Required(CONF_TOKEN): str,
})


async def _validate(hass: HomeAssistant, pdl: str, token: str) -> bool:
    url = f"{API_BASE}/valid_access/{pdl}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={"Authorization": token}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            return resp.status == 200


class MyElectricalDataConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            pdl = user_input[CONF_PDL].strip()
            token = user_input[CONF_TOKEN].strip()
            try:
                valid = await _validate(self.hass, pdl, token)
                if valid:
                    await self.async_set_unique_id(pdl)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Linky {pdl}",
                        data={CONF_PDL: pdl, CONF_TOKEN: token},
                    )
                errors["base"] = "invalid_auth"
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )
