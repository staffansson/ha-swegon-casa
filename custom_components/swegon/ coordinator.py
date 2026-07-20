from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import SwegonCasaClient

_LOGGER = logging.getLogger(__name__)


class SwegonCasaCoordinator(
    DataUpdateCoordinator[dict[str, Any]]
):
    def __init__(
        self,
        hass: HomeAssistant,
        client: SwegonCasaClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Swegon CASA",
            update_interval=None,
        )

        self.client = client
        self.data = {
            "connected": False,
            "values": {},
            "connection_info": {},
        }

        self._unsubscribe_callback = client.register_callback(
            self._handle_push_update
        )

        self._reconnect_task: asyncio.Task | None = None

    async def async_start(self) -> None:
        try:
            await self.client.async_connect()
        except Exception as err:
            raise UpdateFailed(
                f"Unable to connect to Swegon CASA: {err}"
            ) from err

    @callback
    def _handle_push_update(self, update: dict[str, Any]) -> None:
        new_data = {
            "connected": update.get(
                "connected",
                self.data.get("connected", False),
            ),
            "values": {
                **self.data.get("values", {}),
                **update.get("values", {}),
            },
            "connection_info": {
                **self.data.get("connection_info", {}),
                **update.get("connection_info", {}),
            },
        }

        self.async_set_updated_data(new_data)

        if not new_data["connected"]:
            self._schedule_reconnect()

    @callback
    def _schedule_reconnect(self) -> None:
        if self._reconnect_task and not self._reconnect_task.done():
            return

        self._reconnect_task = self.hass.async_create_task(
            self._async_reconnect(),
            "swegon_casa_reconnect",
        )

    async def _async_reconnect(self) -> None:
        delay = 5

        while not self.client.connected:
            await asyncio.sleep(delay)

            try:
                await self.client.async_connect()
                return
            except Exception:
                _LOGGER.warning(
                    "Unable to reconnect to Swegon CASA; retrying"
                )
                delay = min(delay * 2, 300)

    async def async_shutdown(self) -> None:
        self._unsubscribe_callback()

        if self._reconnect_task:
            self._reconnect_task.cancel()

        await self.client.async_disconnect()