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
    OBJECT_FAN_MODE,
    OBJECT_FIREPLACE,
    OBJECT_HUMIDITY,
    OBJECT_HUMIDITY_AMOUNT,
    OBJECT_INTAKE_TEMPERATURE,
    OBJECT_POWER_OFF,
    OBJECT_RETURN_TEMPERATURE,
    OBJECT_SUPPLY_TEMPERATURE,
    OBJECT_VENTILATION_IN,
    OBJECT_VENTILATION_OUT,
)
from .coordinator import SwegonCasaCoordinator
from .entity import SwegonCasaEntity

STATUS_HOME = "home"
STATUS_AWAY = "away"
STATUS_BOOST = "boost"
STATUS_TRAVEL = "travel"
STATUS_FIREPLACE = "fireplace"
STATUS_OFF = "off"
STATUS_AUTO_HUMIDITY = "automatic_humidity"
STATUS_SUMMER_NIGHT = "summer_night_cooling"

OPERATING_STATUS_OPTIONS = [
    STATUS_HOME,
    STATUS_AWAY,
    STATUS_BOOST,
    STATUS_TRAVEL,
    STATUS_FIREPLACE,
    STATUS_OFF,
    STATUS_AUTO_HUMIDITY,
    STATUS_SUMMER_NIGHT,
]

FAN_VALUE_TO_STATUS = {
    1: STATUS_AWAY,
    2: STATUS_HOME,
    3: STATUS_BOOST,
    4: STATUS_TRAVEL,
}


def _as_int(value: Any) -> int | None:
    """Convert a Swegon value to int when possible."""
    if value is None:
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None

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
    device_id = entry.data[CONF_DEVICE_ID]
    device_name = entry.data[CONF_DEVICE_NAME]

    entities: list[SensorEntity] = [
        SwegonCasaSensor(
            coordinator,
            device_id,
            device_name,
            description,
        )
        for description in SENSORS
    ]

    entities.append(
        SwegonCasaOperatingStatusSensor(
            coordinator,
            device_id,
            device_name,
        )
    )

    async_add_entities(entities)


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

class SwegonCasaOperatingStatusSensor(
    SwegonCasaEntity,
    SensorEntity,
):
    """Report the effective operating status."""

    _attr_translation_key = "operating_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = OPERATING_STATUS_OPTIONS

    def __init__(
        self,
        coordinator: SwegonCasaCoordinator,
        device_id: str,
        device_name: str,
    ) -> None:
        # Detta är ett syntetiskt objekt-id som endast används för
        # entitetens unika id. Sensorn kombinerar flera riktiga objekt.
        super().__init__(
            coordinator,
            device_id,
            device_name,
            "operating_status",
        )

    @property
    def native_value(self) -> str | None:
        """Return the effective status shown by the unit."""
        values = self.coordinator.data.get("values", {})

        fireplace_value = _as_int(
            values.get(OBJECT_FIREPLACE)
        )
        power_off_value = _as_int(
            values.get(OBJECT_POWER_OFF)
        )
        fan_mode_value = _as_int(
            values.get(OBJECT_FAN_MODE)
        )

        # Priority:
        # 1. Stopped
        # 2. Fireplace
        # 3. Smart functions
        # 4. Modes

        if power_off_value == 1:
            return STATUS_OFF

        if fireplace_value == 1:
            return STATUS_FIREPLACE

        # Vi vet ännu inte vilka objekt som anger att dessa funktioner
        # faktiskt är aktiva. OBJECT_AUTO_HUMIDITY_MODE och
        # OBJECT_SUMMER_NIGHT_MODE verkar vara inställningar, inte status.
        #
        # När statusobjekten identifierats läggs exempelvis detta till:
        #
        # if automatic_humidity_active == 1:
        #     return STATUS_AUTO_HUMIDITY
        #
        # if summer_night_active == 1:
        #     return STATUS_SUMMER_NIGHT

        return FAN_VALUE_TO_STATUS.get(fan_mode_value)