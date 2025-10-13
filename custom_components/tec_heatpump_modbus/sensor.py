"""Support for TEC Heat Pump Modbus sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSORS
from . import TECHeatPumpCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the TEC Heat Pump sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        TECHeatPumpSensor(coordinator, sensor_config)
        for sensor_config in SENSORS
    ]
    
    async_add_entities(entities)


class TECHeatPumpSensor(CoordinatorEntity[TECHeatPumpCoordinator], SensorEntity):
    """Representation of a TEC Heat Pump sensor."""
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TECHeatPumpCoordinator,
        sensor_config: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self._sensor_config = sensor_config

        self.entity_description = SensorEntityDescription(
            key=sensor_config["unique_id"],
            translation_key=sensor_config.get("translation_key"),
            name=sensor_config.get("name"),
            device_class=sensor_config.get("device_class"),
            native_unit_of_measurement=sensor_config.get("unit"),
            state_class=sensor_config.get("state_class"),
        )
        
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{sensor_config['unique_id']}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str | int | float | None:
        """Return the state of the sensor."""
        value = self.coordinator.data.get(self.entity_description.key)
        
        if "value_map" in self._sensor_config and value is not None:
            return self._sensor_config["value_map"].get(value, value)
            
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device specific state attributes."""
        return {
            "address": self._sensor_config["address"],
            "device_id": self.coordinator.device_id,
            "data_type": self._sensor_config["data_type"],
            "function": self._sensor_config["function"],
        }