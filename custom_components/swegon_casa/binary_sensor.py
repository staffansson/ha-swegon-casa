from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE_ID, CONF_DEVICE_NAME
from .coordinator import SwegonCasaCoordinator
from .entity import SwegonCasaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SwegonCasaCoordinator = entry.runtime_data

    async_add_entities(
        [
            SwegonCasaConnectionSensor(
                coordinator,
                entry.data[CONF_DEVICE_ID],
                entry.data[CONF_DEVICE_NAME],
            )
        ]
    )


class SwegonCasaConnectionSensor(
    SwegonCasaEntity,
    BinarySensorEntity,
):
    _attr_translation_key = "cloud_connection"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator,
        device_id,
        device_name,
    ) -> None:
        super().__init__(
            coordinator,
            device_id,
            device_name,
            "connection",
        )

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("connected"))