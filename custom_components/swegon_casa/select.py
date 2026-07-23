from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    OBJECT_FAN_MODE,
    OBJECT_FIREPLACE_MODE,
    OBJECT_POWER_OFF,
    OBJECT_SMART_HUMIDITY_LEVEL,
    OBJECT_SUMMER_NIGHT_COOLING_BOOST_LEVEL,
    OBJECT_SUMMER_NIGHT_COOLING_ACTIVATION_LEVEL,
)
from .coordinator import SwegonCasaCoordinator
from .entity import SwegonCasaEntity

MODE_HOME = "home"
MODE_AWAY = "away"
MODE_BOOST = "boost"
MODE_TRAVEL = "travel"
MODE_FIREPLACE = "fireplace"
MODE_OFF = "off"

LEVEL_OFF = "off"
LEVEL_LOW = "low"
LEVEL_NORMAL = "normal"
LEVEL_MEDIUM = "medium"
LEVEL_HIGH = "high"
LEVEL_FULL = "full"
LEVEL_USER = "user"

OPTIONS = [
    MODE_HOME,
    MODE_AWAY,
    MODE_BOOST,
    MODE_TRAVEL,
    MODE_FIREPLACE,
    MODE_OFF,
]

# Values from object 111
FAN_MODE_VALUES = {
    MODE_AWAY: 1,
    MODE_HOME: 2,
    MODE_BOOST: 3,
}

FAN_VALUE_TO_MODE = {
    1: MODE_AWAY,
    2: MODE_HOME,
    3: MODE_BOOST,
    4: MODE_TRAVEL,
}

SMART_HUMIDITY_OPTIONS = [
    LEVEL_OFF,
    LEVEL_LOW,
    LEVEL_NORMAL,
    LEVEL_HIGH,
    LEVEL_FULL,
    LEVEL_USER,
]

SMART_HUMIDITY_OPTION_TO_VALUE = {
    LEVEL_OFF: 0,
    LEVEL_LOW: 1,
    LEVEL_NORMAL: 2,
    LEVEL_HIGH: 3,
    LEVEL_FULL: 4,
    LEVEL_USER: 5,
}

SMART_HUMIDITY_VALUE_TO_OPTION = {
    value: option
    for option, value in SMART_HUMIDITY_OPTION_TO_VALUE.items()
}

SUMMER_NIGHT_COOLING_BOOST_OPTIONS = [
    LEVEL_OFF,
    LEVEL_LOW,
    LEVEL_NORMAL,
    LEVEL_HIGH,
    LEVEL_FULL,
    LEVEL_USER,
]

SUMMER_NIGHT_COOLING_BOOST_OPTION_TO_VALUE = {
    LEVEL_OFF: 0,
    LEVEL_LOW: 1,
    LEVEL_NORMAL: 2,
    LEVEL_HIGH: 3,
    LEVEL_FULL: 4,
    LEVEL_USER: 5,
}

SUMMER_NIGHT_COOLING_BOOST_VALUE_TO_OPTION = {
    value: option
    for option, value in SUMMER_NIGHT_COOLING_BOOST_OPTION_TO_VALUE.items()
}

SUMMER_NIGHT_ACTIVATION_OPTIONS = [
    LEVEL_OFF,
    LEVEL_LOW,
    LEVEL_NORMAL,
    LEVEL_HIGH,
    LEVEL_FULL,
    LEVEL_USER,
]

SUMMER_NIGHT_ACTIVATION_OPTION_TO_VALUE = {
    LEVEL_OFF: 0,
    LEVEL_LOW: 1,
    LEVEL_NORMAL: 2,
    LEVEL_HIGH: 3,
    LEVEL_FULL: 4,
    LEVEL_USER: 5,
}

SUMMER_NIGHT_ACTIVATION_VALUE_TO_OPTION = {
    value: option
    for option, value in SUMMER_NIGHT_ACTIVATION_OPTION_TO_VALUE.items()
}



def _as_int(value: Any) -> int | None:
    """Convert a Swegon value to int when possible."""
    if value is None:
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None

async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SwegonCasaCoordinator = entry.runtime_data

    async_add_entities(
    [
        SwegonCasaModeSelect(
            coordinator,
            entry.data[CONF_DEVICE_ID],
            entry.data[CONF_DEVICE_NAME],
        ),
        SwegonCasaMappedSelect(
            coordinator=coordinator,
            device_id=entry.data[CONF_DEVICE_ID],
            device_name=entry.data[CONF_DEVICE_NAME],
            object_id=OBJECT_SMART_HUMIDITY_LEVEL,
            translation_key="smart_humidity_control_level",
            options=SMART_HUMIDITY_OPTIONS,
            option_to_value=SMART_HUMIDITY_OPTION_TO_VALUE,
            value_to_option=SMART_HUMIDITY_VALUE_TO_OPTION,
        ),
        SwegonCasaMappedSelect(
            coordinator=coordinator,
            device_id=entry.data[CONF_DEVICE_ID],
            device_name=entry.data[CONF_DEVICE_NAME],
            object_id=OBJECT_SUMMER_NIGHT_COOLING_BOOST_LEVEL,
            translation_key="summer_night_cooling_boost_level",
            options=SUMMER_NIGHT_COOLING_BOOST_OPTIONS,
            option_to_value=SUMMER_NIGHT_COOLING_BOOST_OPTION_TO_VALUE,
            value_to_option=SUMMER_NIGHT_COOLING_BOOST_VALUE_TO_OPTION,
        ),
        SwegonCasaMappedSelect(
            coordinator=coordinator,
            device_id=entry.data[CONF_DEVICE_ID],
            device_name=entry.data[CONF_DEVICE_NAME],
            object_id=OBJECT_SUMMER_NIGHT_COOLING_ACTIVATION_LEVEL,
            translation_key="summer_night_cooling_activation_level",
            options=SUMMER_NIGHT_ACTIVATION_OPTIONS,
            option_to_value=SUMMER_NIGHT_ACTIVATION_OPTION_TO_VALUE,
            value_to_option=SUMMER_NIGHT_ACTIVATION_VALUE_TO_OPTION,
        ),
    ]
)


class SwegonCasaModeSelect(SwegonCasaEntity, SelectEntity):
    """Select the requested operating mode."""
    _attr_translation_key = "operating_mode"
    _attr_options = OPTIONS

    def __init__(
        self,
        coordinator: SwegonCasaCoordinator,
        device_id: str,
        device_name: str,
    ) -> None:
        super().__init__(
            coordinator,
            device_id,
            device_name,
            OBJECT_FAN_MODE,
        )

    @property
    def current_option(self) -> str | None:
        """Return the currently selectable operating status."""
        values = self.coordinator.data.get("values", {})

        fireplace_value = _as_int(values.get(OBJECT_FIREPLACE_MODE))
        power_off_value = _as_int(values.get(OBJECT_POWER_OFF))
        fan_mode_value = _as_int(values.get(OBJECT_FAN_MODE))

        if fireplace_value == 1:
            return MODE_FIREPLACE

        if power_off_value == 1:
            return MODE_OFF

        return FAN_VALUE_TO_MODE.get(fan_mode_value)

    async def async_select_option(self, option: str) -> None:
        """Select an operating mode."""
        client = self.coordinator.client
        values = self.coordinator.data.get("values", {})

        fireplace_active = (
            _as_int(values.get(OBJECT_FIREPLACE_MODE)) == 1
        )

        # Chosing a regular mode stops current fireplace-function
        if option != MODE_FIREPLACE and fireplace_active:
            await client.async_write(OBJECT_FIREPLACE_MODE, 0)

        if option in FAN_MODE_VALUES:
            await client.async_write(OBJECT_FAN_MODE,FAN_MODE_VALUES[option])

        elif option == MODE_TRAVEL:
            await client.async_write("112", 1)
            await client.async_write("154", 1)

        elif option == MODE_FIREPLACE:
            await client.async_write(OBJECT_FIREPLACE_MODE, 1)

        elif option == MODE_OFF:
            await client.async_write(OBJECT_POWER_OFF, 1)

        self.async_write_ha_state()

class SwegonCasaMappedSelect(SwegonCasaEntity, SelectEntity):
    """Select a mapped Swegon CASA configuration value."""

    def __init__(
        self,
        coordinator: SwegonCasaCoordinator,
        device_id: str,
        device_name: str,
        object_id: str,
        translation_key: str,
        options: list[str],
        option_to_value: dict[str, int],
    ) -> None:
        """Initialize the mapped select entity."""
        super().__init__(
            coordinator,
            device_id,
            device_name,
            object_id,
        )

        self._attr_translation_key = translation_key
        self._attr_options = options

        self._option_to_value = option_to_value
        self._value_to_option = {
            value: option
            for option, value in option_to_value.items()
        }

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        value = _as_int(self.raw_value)

        if value is None:
            return None

        return self._value_to_option.get(value)

    async def async_select_option(self, option: str) -> None:
        """Write the selected option to Swegon CASA."""
        if option not in self._option_to_value:
            raise ValueError(
                f"Unsupported option {option!r} for "
                f"Swegon object {self._object_id}"
            )

        value = self._option_to_value[option]

        await self.coordinator.client.async_write(
            self._object_id,
            value,
        )