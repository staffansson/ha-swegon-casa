from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    SwegonCasaAuthenticationError,
    SwegonCasaClient,
    SwegonCasaConnectionError,
)
from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_SERIAL_NUMBER,
    DOMAIN,
)


class SwegonCasaConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    VERSION = 1

    def __init__(self) -> None:
        self._username: str | None = None
        self._password: str | None = None
        self._devices: list[dict] = []

    async def async_step_user(
        self,
        user_input=None,
    ):
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            client = SwegonCasaClient(
                async_get_clientsession(self.hass),
                username,
                password,
            )

            try:
                devices = await client.async_login()

            except SwegonCasaAuthenticationError:
                errors["base"] = "invalid_auth"

            except SwegonCasaConnectionError:
                errors["base"] = "cannot_connect"

            except Exception:
                errors["base"] = "unknown"

            else:
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    self._username = username
                    self._password = password
                    self._devices = devices

                    return await self.async_step_device()

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_device(
        self,
        user_input=None,
    ):
        device_map = {}

        for device in self._devices:
            device_id = str(
                device.get("id")
                or device.get("deviceid")
                or device.get("deviceId")
            )

            name = (
                device.get("name")
                or device.get("devicename")
                or device_id
            )

            device_map[device_id] = name

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]

            device = next(
                item
                for item in self._devices
                if str(
                    item.get("id")
                    or item.get("deviceid")
                    or item.get("deviceId")
                )
                == device_id
            )

            device_name = device_map[device_id]
            serial_number = str(
                device.get("serialnumber")
                or device.get("serialNumber")
                or device_id
            )

            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=device_name,
                data={
                    CONF_USERNAME: self._username,
                    CONF_PASSWORD: self._password,
                    CONF_DEVICE_ID: device_id,
                    CONF_DEVICE_NAME: device_name,
                    CONF_SERIAL_NUMBER: serial_number,
                },
            )

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): vol.In(
                        device_map
                    )
                }
            ),
        )