from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    OBJECT_FAN_MODE,
    OBJECT_FIREPLACE_MODE,
    OBJECT_POWER_OFF,
)
from .coordinator import SwegonCasaCoordinator
from .entity import SwegonCasaEntity

MODE_HOME = "home"
MODE_AWAY = "away"
MODE_BOOST = "boost"
MODE_TRAVEL = "travel"
MODE_FIREPLACE = "fireplace"
MODE_OFF = "off"

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
            )
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