"""Number platform for TEC Heat Pump Modbus (writable holding registers)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NUMBERS
from . import TECHeatPumpCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the TEC Heat Pump number entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        TECHeatPumpNumber(coordinator, number_config)
        for number_config in NUMBERS
    ]

    async_add_entities(entities)


class TECHeatPumpNumber(CoordinatorEntity[TECHeatPumpCoordinator], NumberEntity):
    """A writable holding register exposed as a number entity.

    The coordinator stores values already scaled to display units
    (raw 213 with scale 0.1 -> 21.3). Writes apply the inverse scaling
    (21.3 / 0.1 -> raw 213) before hitting Modbus.
    """

    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: TECHeatPumpCoordinator,
        number_config: dict[str, Any],
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)

        self._number_config = number_config
        scale = number_config.get("scale", 1.0)

        # min_value/max_value in const.py are raw register values; convert
        # to display units so HA enforces the documented range on input.
        self.entity_description = NumberEntityDescription(
            key=number_config["unique_id"],
            translation_key=number_config.get("translation_key"),
            name=number_config.get("name"),
            device_class=number_config.get("device_class"),
            native_unit_of_measurement=number_config.get("unit"),
            native_min_value=round(number_config["min_value"] * scale, 3),
            native_max_value=round(number_config["max_value"] * scale, 3),
            native_step=scale,
        )

        self._attr_unique_id = f"{coordinator.entry.entry_id}_{number_config['unique_id']}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | None:
        """Return the current (scaled) register value."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None
        # Trim float artifacts from raw * scale (213 * 0.1 = 21.3000...01)
        return round(value, 3)

    async def async_set_native_value(self, value: float) -> None:
        """Write a new value to the holding register."""
        scale = self._number_config.get("scale", 1.0)
        # round() instead of int(): int(21.3 / 0.1) truncates to 212
        raw_value = round(value / scale)
        # Two's complement for signed registers (e.g. -10.0°C -> 65436)
        if raw_value < 0:
            raw_value += 65536

        _LOGGER.debug(
            "Writing %s=%s (raw %s) to address %s",
            self.entity_description.key,
            value,
            raw_value,
            self._number_config["address"],
        )
        await self.coordinator.api_write_register(
            address=self._number_config["address"],
            value=raw_value,
            device_id=self.coordinator.device_id,
        )
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device specific state attributes."""
        return {
            "address": self._number_config["address"],
            "device_id": self.coordinator.device_id,
            "data_type": self._number_config["data_type"],
            "function": self._number_config["function"],
        }
