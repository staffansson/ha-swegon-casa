from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SwegonCasaCoordinator


class SwegonCasaEntity(
    CoordinatorEntity[SwegonCasaCoordinator]
):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SwegonCasaCoordinator,
        device_id: str,
        device_name: str,
        object_id: str,
    ) -> None:
        super().__init__(coordinator)

        self._device_id = device_id
        self._object_id = object_id

        self._attr_unique_id = f"{device_id}_{object_id}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            manufacturer="Swegon",
            model="CASA Smart",
            configuration_url="https://swegoncasa.io/",
        )

    @property
    def available(self) -> bool:
        return bool(self.coordinator.data.get("connected"))

    @property
    def raw_value(self):
        return self.coordinator.data.get(
            "values",
            {},
        ).get(self._object_id)