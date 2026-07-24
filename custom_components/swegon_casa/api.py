from __future__ import annotations

import asyncio
import ssl
import json
import logging
from collections.abc import Callable
from typing import Any

import aiohttp
import websockets
from websockets.asyncio.client import ClientConnection

from .const import (
    DEVICE_ADDRESS,
    KEEPALIVE_INTERVAL,
    LOGIN_URL,
    OBJECT_DEVICE_INFO,
    ORIGIN,
    PROPERTY_VALUE,
    SUBSCRIBED_OBJECTS,
    WEBSOCKET_URL,
)

_LOGGER = logging.getLogger(__name__)

DEBUG_LOGGING = False

# Object discovery is separate from normal detailed logging.
# Enabling this subscribes to a large object range.
DEBUG_DISCOVER_OBJECTS = False
DEBUG_OBJECT_ID_MIN = 1
DEBUG_OBJECT_ID_MAX = 500

if DEBUG_LOGGING:
    _LOGGER.setLevel(logging.DEBUG)

def _debug(message: str, *args: Any) -> None:
    """Log detailed protocol information when debug is enabled."""
    if DEBUG_LOGGING:
        _LOGGER.debug(message, *args)

class SwegonCasaError(Exception):
    """Base exception."""


class SwegonCasaAuthenticationError(SwegonCasaError):
    """Authentication failed."""


class SwegonCasaConnectionError(SwegonCasaError):
    """Connection failed."""


class SwegonCasaClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        device_id: str | None = None,
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._device_id = device_id

        self._token: str | None = None
        self._websocket: ClientConnection | None = None
        self._listen_task: asyncio.Task | None = None
        self._keepalive_task: asyncio.Task | None = None

        self._ssl_context: ssl.SSLContext | None = None

        self._callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._connected = False
        self._closing = False

        self._seen_object_ids: set[str] = set()

    @property
    def connected(self) -> bool:
        return self._connected

    def register_callback(
        self,
        callback: Callable[[dict[str, Any]], None],
    ) -> Callable[[], None]:
        self._callbacks.append(callback)

        def unsubscribe() -> None:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

        return unsubscribe

    async def async_login(self) -> list[dict[str, Any]]:
        payload = {
            "type": "client",
            "tag": "ouman/swegon",
            "username": self._username,
            "password": self._password,
        }

        try:
            async with self._session.post(
                LOGIN_URL,
                json=payload,
                headers={"Origin": ORIGIN},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                if response.status in (401, 403):
                    raise SwegonCasaAuthenticationError(
                        "Invalid username or password"
                    )

                response.raise_for_status()
                data = await response.json()

        except aiohttp.ClientResponseError as err:
            raise SwegonCasaConnectionError(
                f"Login HTTP error: {err.status}"
            ) from err
        except aiohttp.ClientError as err:
            raise SwegonCasaConnectionError(
                f"Unable to contact login service: {err}"
            ) from err

        token = data.get("token")
        if not token:
            raise SwegonCasaAuthenticationError(
                "Login succeeded but no token was returned"
            )

        self._token = token

        devices = data.get("devices", [])

        _debug(
            "Swegon CASA login succeeded; %s device(s) returned",
            len(devices),
        )

        return devices

    async def async_connect(self) -> None:
        if not self._device_id:
            raise SwegonCasaConnectionError("No device ID configured")

        _debug(
            "Connecting to Swegon CASA WebSocket for device %s",
            self._device_id,
        )

        if not self._token:
            await self.async_login()

        self._closing = False

        try:
            if self._ssl_context is None:
                loop = asyncio.get_running_loop()
                self._ssl_context = await loop.run_in_executor(
                    None,
                    ssl.create_default_context,
                )

            self._websocket = await websockets.connect(
                WEBSOCKET_URL,
                origin=ORIGIN,
                open_timeout=20,
                close_timeout=10,
            )
        except Exception as err:
            raise SwegonCasaConnectionError(
                f"Unable to connect to websocket: {err}"
            ) from err

        self._connected = True

        _LOGGER.info(
            "Connected to Swegon CASA device %s",
            self._device_id,
        )


        await self._async_send_connect_packet()

        self._listen_task = asyncio.create_task(
            self._async_listen(),
            name="swegon_casa_listener",
        )

        self._keepalive_task = asyncio.create_task(
            self._async_keepalive(),
            name="swegon_casa_keepalive",
        )

    async def _async_send_connect_packet(self) -> None:
        assert self._websocket is not None

        connect_data = {
            "deviceid": self._device_id,
            "date": self._iso_timestamp(),
            "token": self._token,
        }

        _debug(
            "Sending Socket.IO connect packet for device %s at %s",
            self._device_id,
            connect_data["date"],
        )
        await self._websocket.send(
            f"40{json.dumps(connect_data, separators=(',', ':'))}"
        )

    async def _async_subscribe(self) -> None:
        read_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "read",
            "params": {
                "objects": [
                    {
                        "id": OBJECT_DEVICE_INFO,
                        "device": DEVICE_ADDRESS,
                        "properties": {"948": {}},
                    }
                ]
            },
        }

        if DEBUG_DISCOVER_OBJECTS:
            subscribed_object_ids = [
                str(object_id)
                for object_id in range(
                    DEBUG_OBJECT_ID_MIN,
                    DEBUG_OBJECT_ID_MAX + 1,
                )
            ]

            _LOGGER.warning(
                "Swegon CASA object discovery is enabled; subscribing to objects %s-%s",
                DEBUG_OBJECT_ID_MIN,
                DEBUG_OBJECT_ID_MAX,
            )
        else:
            subscribed_object_ids = list(SUBSCRIBED_OBJECTS)
        
        _debug(
            "Subscribing to %s Swegon CASA objects: %s",
            len(subscribed_object_ids),
            subscribed_object_ids,
        )

        subscribe_message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "subscribe",
            "params": {
                "objects": [
                    {
                        "id": object_id,
                        "device": DEVICE_ADDRESS,
                        "properties": {PROPERTY_VALUE: {}},
                    }
                    for object_id in subscribed_object_ids
                ]
            },
        }

        await self._async_send_rpc(read_message)
        await self._async_send_rpc(subscribe_message)

    async def _async_send_rpc(self, message: dict[str, Any]) -> None:
        """Send a JSON-RPC message."""
        if not self._websocket:
            raise SwegonCasaConnectionError(
                "Websocket is not connected"
            )

        _debug(
            "Sending Swegon CASA RPC message: %s",
            json.dumps(message, separators=(",", ":")),
        )

        socket_io_message = [
            "message",
            json.dumps(message, separators=(",", ":")),
        ]

        await self._websocket.send(
            f"42{json.dumps(socket_io_message, separators=(',', ':'))}"
        )

    async def async_write(
        self,
        object_id: str,
        value: int | float,
    ) -> None:
        """Write a value to a Swegon CASA object."""
        _debug(
            "Writing Swegon CASA object %s with value %r",
            object_id,
            value,
        )

        message = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "write",
            "params": {
                "objects": [
                    {
                        "id": object_id,
                        "device": DEVICE_ADDRESS,
                        "properties": {
                            PROPERTY_VALUE: {
                                "value": value,
                            }
                        },
                    }
                ]
            },
        }

        await self._async_send_rpc(message)

    async def _async_keepalive(self) -> None:
        try:
            while not self._closing and self._websocket:
                await asyncio.sleep(KEEPALIVE_INTERVAL)

                if self._websocket:
                    _debug("Sending Swegon CASA keepalive pong")
                    await self._websocket.send("3")

        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Swegon keepalive failed")

    async def _async_listen(self) -> None:
        assert self._websocket is not None

        try:
            async for raw_message in self._websocket:
                await self._async_handle_message(str(raw_message))

        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Swegon websocket listener failed")
        finally:
            self._connected = False
            self._notify_callbacks({"connected": False})

    async def _async_handle_message(self, raw: str) -> None:
        _debug("Received raw Swegon CASA message: %s", raw)

        if raw.startswith("0"):
            await self._async_send_connect_packet()
            return

        if raw == "2":
            if self._websocket:
                await self._websocket.send("3")
            return

        if raw.startswith("44"):
            raise SwegonCasaConnectionError(
                f"Socket.IO error: {raw}"
            )

        if not raw.startswith("42"):
            return

        try:
            socket_message = json.loads(raw[2:])

            if len(socket_message) < 2:
                return

            rpc_message = json.loads(socket_message[1])

        except (json.JSONDecodeError, TypeError, IndexError):
            _LOGGER.warning("Could not parse Swegon message")
            return

        if rpc_message.get("method") == "device_connected":
            self._connected = True

            _debug(
                "Swegon CASA device connected: %s",
                rpc_message.get("params", {}),
            )
            await self._async_subscribe()

            self._notify_callbacks(
                {
                    "connected": True,
                    "connection_info": rpc_message.get("params", {}),
                }
            )
            return

        if rpc_message.get("method") != "value":
            return

        objects = rpc_message.get("params", {}).get("objects", [])

        updates: dict[str, Any] = {}

        for obj in objects:
            object_id = str(obj.get("id"))
            properties = obj.get("properties", {})

            # Log every property, even if it is not property 85.
            for property_id, property_data in properties.items():
                if not isinstance(property_data, dict):
                    continue

                property_value = property_data.get("value")

                _debug(
                    "Swegon CASA object update: object=%s property=%s value=%r",
                    object_id,
                    property_id,
                    property_value,
                )

            value_data = properties.get(PROPERTY_VALUE, {})
            value = value_data.get("value")

            if object_id not in self._seen_object_ids:
                self._seen_object_ids.add(object_id)

                _debug(
                    "First update for Swegon CASA object %s: properties=%s",
                    object_id,
                    properties,
                )

            if value is not None:
                updates[object_id] = value

        if updates:
            _debug(
                "Forwarding %s Swegon CASA value update(s): %s",
                len(updates),
                updates,
            )
            self._notify_callbacks(
                {
                    "connected": True,
                    "values": updates,
                }
            )

    def _notify_callbacks(self, data: dict[str, Any]) -> None:
        for callback in list(self._callbacks):
            try:
                callback(data)
            except Exception:
                _LOGGER.exception("Swegon callback failed")

    async def async_disconnect(self) -> None:
        _LOGGER.info(
            "Disconnecting from Swegon CASA device %s",
            self._device_id,
        )
        self._closing = True

        for task in (self._listen_task, self._keepalive_task):
            if task:
                task.cancel()

        if self._websocket:
            await self._websocket.close()
        
        _debug(
            "Swegon CASA device %s disconnected",
            self._device_id,
        )

        self._websocket = None
        self._connected = False
        

    @staticmethod
    def _iso_timestamp() -> str:
        from datetime import UTC, datetime

        return datetime.now(UTC).isoformat()