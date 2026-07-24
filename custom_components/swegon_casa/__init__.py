from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
)
from homeassistant.helpers.aiohttp_client import (
    async_get_clientsession,
)

from .api import (
    SwegonCasaAuthenticationError,
    SwegonCasaClient,
    SwegonCasaConnectionError,
)
from .const import CONF_DEVICE_ID, PLATFORMS
from .coordinator import SwegonCasaCoordinator

_LOGGER = logging.getLogger(__name__)

type SwegonCasaConfigEntry = ConfigEntry[
    SwegonCasaCoordinator
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SwegonCasaConfigEntry,
) -> bool:
    client = SwegonCasaClient(
        async_get_clientsession(hass),
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_DEVICE_ID],
    )

    coordinator = SwegonCasaCoordinator(
        hass,
        client,
    )

    try:
        await client.async_login()
        await coordinator.async_start()

    except SwegonCasaAuthenticationError as err:
        raise ConfigEntryAuthFailed from err

    except SwegonCasaConnectionError as err:
        raise ConfigEntryNotReady from err

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: SwegonCasaConfigEntry,
) -> bool:
    unload_ok = (
        await hass.config_entries.async_unload_platforms(
            entry,
            PLATFORMS,
        )
    )

    if unload_ok:
        await entry.runtime_data.async_shutdown()

    return unload_ok