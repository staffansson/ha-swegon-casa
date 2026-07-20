from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    OBJECT_AIR_QUALITY,
    OBJECT_BOOST_COUNTDOWN,
    OBJECT_CO2,
    OBJECT_CURRENT_FAN_SPEED,
    OBJECT_HUMIDITY,
    OBJECT_HUMIDITY_AMOUNT,
    OBJECT_INTAKE_TEMPERATURE,
    OBJECT_RETURN_TEMPERATURE,
    OBJECT_SUPPLY_TEMPERATURE,
    OBJECT_VENTILATION_IN,
    OBJECT_VENTILATION_OUT,
)
from .coordinator import SwegonCasaCoordinator
from .entity import SwegonCasaEntity


@dataclass(frozen=True, kw_only=True)
class SwegonSensorDescription(SensorEntityDescription):
    object_id: str


SENSORS = (
    SwegonSensorDescription(
        key="supply_temperature",
        translation_key="supply_temperature",
        object_id=OBJECT_SUPPLY_TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SwegonSensorDescription(
        key="return_temperature",
        translation_key="return_temperature",
        object_id=OBJECT_RETURN_TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SwegonSensorDescription(
        key="intake_temperature",
        translation_key="intake_temperature",
        object_id=OBJECT_INTAKE_TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SwegonSensorDescription(
        key="humidity",
        translation_key="humidity",
        object_id=OBJECT_HUMIDITY,
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SwegonSensorDescription(
        key="absolute_humidity",
        translation_key="absolute_humidity",
        object_id=OBJECT_HUMIDITY_AMOUNT,
        native_unit_of_measurement="g/m³",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SwegonSensorDescription(
        key="co2",
        translation_key="co2",
        object_id=OBJECT_CO2,
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SwegonSensorDescription(
        key="air_quality",
        translation_key="air_quality",
        object_id=OBJECT_AIR_QUALITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SwegonSensorDescription(
        key="fan_speed",
        translation_key="fan_speed",
        object_id=OBJECT_CURRENT_FAN_SPEED,
    ),
    SwegonSensorDescription(
        key="ventilation_in",
        translation_key="ventilation_in",
        object_id=OBJECT_VENTILATION_IN,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SwegonSensorDescription(
        key="ventilation_out",
        translation_key="ventilation_out",
        object_id=OBJECT_VENTILATION_OUT,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SwegonSensorDescription(
        key="boost_countdown",
        translation_key="boost_countdown",
        object_id=OBJECT_BOOST_COUNTDOWN,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SwegonCasaCoordinator = entry.runtime_data

    async_add_entities(
        SwegonCasaSensor(
            coordinator,
            entry.data[CONF_DEVICE_ID],
            entry.data[CONF_DEVICE_NAME],
            description,
        )
        for description in SENSORS
    )


class SwegonCasaSensor(SwegonCasaEntity, SensorEntity):
    entity_description: SwegonSensorDescription

    def __init__(
        self,
        coordinator: SwegonCasaCoordinator,
        device_id: str,
        device_name: str,
        description: SwegonSensorDescription,
    ) -> None:
        super().__init__(
            coordinator,
            device_id,
            device_name,
            description.object_id,
        )

        self.entity_description = description

    @property
    def native_value(self) -> Any:
        value = self.raw_value

        if value is None:
            return None

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return value

        if (
            self.entity_description.object_id
            == OBJECT_HUMIDITY_AMOUNT
        ):
            return numeric_value / 10

        return numeric_value