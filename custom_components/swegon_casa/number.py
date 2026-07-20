from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    OBJECT_AWAY_TEMPERATURE_DROP,
    OBJECT_CO2_AWAY_LIMIT,
    OBJECT_CO2_HOME_LIMIT,
    OBJECT_SUPPLY_SETPOINT,
    OBJECT_TRAVEL_TEMPERATURE_DROP,
)
from .coordinator import SwegonCasaCoordinator
from .entity import SwegonCasaEntity


@dataclass(frozen=True, kw_only=True)
class SwegonNumberDescription(NumberEntityDescription):
    object_id: str


NUMBERS = (
    SwegonNumberDescription(
        key="supply_temperature_setpoint",
        translation_key="supply_temperature_setpoint",
        object_id=OBJECT_SUPPLY_SETPOINT,
        native_min_value=12,
        native_max_value=25,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.BOX,
    ),
    SwegonNumberDescription(
        key="co2_home_limit",
        translation_key="co2_home_limit",
        object_id=OBJECT_CO2_HOME_LIMIT,
        native_min_value=400,
        native_max_value=2000,
        native_step=50,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        mode=NumberMode.BOX,
    ),
    SwegonNumberDescription(
        key="co2_away_limit",
        translation_key="co2_away_limit",
        object_id=OBJECT_CO2_AWAY_LIMIT,
        native_min_value=400,
        native_max_value=2000,
        native_step=50,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        mode=NumberMode.BOX,
    ),
    SwegonNumberDescription(
        key="away_temperature_drop",
        translation_key="away_temperature_drop",
        object_id=OBJECT_AWAY_TEMPERATURE_DROP,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    SwegonNumberDescription(
        key="travel_temperature_drop",
        translation_key="travel_temperature_drop",
        object_id=OBJECT_TRAVEL_TEMPERATURE_DROP,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SwegonCasaCoordinator = entry.runtime_data

    async_add_entities(
        SwegonCasaNumber(
            coordinator,
            entry.data[CONF_DEVICE_ID],
            entry.data[CONF_DEVICE_NAME],
            description,
        )
        for description in NUMBERS
    )


class SwegonCasaNumber(SwegonCasaEntity, NumberEntity):
    entity_description: SwegonNumberDescription

    def __init__(
        self,
        coordinator,
        device_id,
        device_name,
        description,
    ) -> None:
        super().__init__(
            coordinator,
            device_id,
            device_name,
            description.object_id,
        )
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        try:
            return float(self.raw_value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.client.async_write(
            self.entity_description.object_id,
            value,
        )