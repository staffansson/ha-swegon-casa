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
    OBJECT_HUMIDITY_BOOST,
    OBJECT_SUMMER_NIGHT_COOLING_BOOST,
    OBJECT_FAN_MODE,
    OBJECT_FIREPLACE_MODE,
    OBJECT_SMART_HUMIDITY_LEVEL,
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

FUNCTION_STATUS_ACTIVE = "active"
FUNCTION_STATUS_INACTIVE = "inactive"

FUNCTION_STATUS_OPTIONS = [
    FUNCTION_STATUS_ACTIVE,
    FUNCTION_STATUS_INACTIVE,
]


def _as_int(value: Any) -> int | None:
    """Convert a Swegon value to int when possible."""
    if value is None:
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None

def _as_float(value: Any) -> float | None:
    """Convert a Swegon value to float when possible."""
    if value is None:
        return None

    try:
        return float(value)
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

    entities.extend(
    [
        SwegonCasaFunctionStatusSensor(
            coordinator=coordinator,
            device_id=device_id,
            device_name=device_name,
            object_id=OBJECT_HUMIDITY_BOOST,
            translation_key="smart_humidity_control",
            unique_key="smart_humidity_control_status",
        ),
        SwegonCasaFunctionStatusSensor(
            coordinator=coordinator,
            device_id=device_id,
            device_name=device_name,
            object_id=OBJECT_SUMMER_NIGHT_COOLING_BOOST,
            translation_key="summer_night_cooling",
            unique_key="summer_night_cooling_status",
        ),
        SwegonCasaBoostPercentageSensor(
            coordinator=coordinator,
            device_id=device_id,
            device_name=device_name,
            object_id=OBJECT_HUMIDITY_BOOST,
            translation_key="smart_humidity_control_effect",
            unique_key="smart_humidity_control_effect",
        ),
        SwegonCasaBoostPercentageSensor(
            coordinator=coordinator,
            device_id=device_id,
            device_name=device_name,
            object_id=OBJECT_SUMMER_NIGHT_COOLING_BOOST,
            translation_key="summer_night_cooling_effect",
            unique_key="summer_night_cooling_effect",
        ),
    ]
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

class SwegonCasaFunctionStatusSensor(
    SwegonCasaEntity,
    SensorEntity,
):
    """Report whether a smart ventilation function is active."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = FUNCTION_STATUS_OPTIONS

    def __init__(
        self,
        coordinator: SwegonCasaCoordinator,
        device_id: str,
        device_name: str,
        object_id: str,
        translation_key: str,
        unique_key: str,
    ) -> None:
        super().__init__(
            coordinator,
            device_id,
            device_name,
            unique_key,
        )

        self._source_object_id = object_id
        self._attr_translation_key = translation_key

    @property
    def native_value(self) -> str | None:
        """Return whether the function currently produces boost."""
        values = self.coordinator.data.get("values", {})
        value = _as_float(values.get(self._source_object_id))

        if value is None:
            return None

        if value > 0:
            return FUNCTION_STATUS_ACTIVE

        return FUNCTION_STATUS_INACTIVE

class SwegonCasaBoostPercentageSensor(
    SwegonCasaEntity,
    SensorEntity,
):
    """Report the current boost level as a percentage."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    def __init__(
        self,
        coordinator: SwegonCasaCoordinator,
        device_id: str,
        device_name: str,
        object_id: str,
        translation_key: str,
        unique_key: str,
    ) -> None:
        super().__init__(
            coordinator,
            device_id,
            device_name,
            unique_key,
        )

        self._source_object_id = object_id
        self._attr_translation_key = translation_key

    @property
    def native_value(self) -> int | None:
        """Return the current 0-20 boost value as 0-100 percent."""
        values = self.coordinator.data.get("values", {})
        value = _as_float(values.get(self._source_object_id))

        if value is None:
            return None

        percentage = round(value / 20 * 100)

        return max(0, min(100, percentage))

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
            values.get(OBJECT_FIREPLACE_MODE)
        )
        power_off_value = _as_int(
            values.get(OBJECT_POWER_OFF)
        )
        fan_mode_value = _as_int(
            values.get(OBJECT_FAN_MODE)
        )

        if power_off_value == 1:
            return STATUS_OFF

        if fireplace_value == 1:
            return STATUS_FIREPLACE

        return FAN_VALUE_TO_STATUS.get(fan_mode_value)