"""Binary sensor platform for TEC Heat Pump Modbus (alarm bits)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, BINARY_SENSORS
from . import TECHeatPumpCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        TECHeatPumpBinarySensor(coordinator, config)
        for config in BINARY_SENSORS
    ]

    async_add_entities(entities)


class TECHeatPumpBinarySensor(CoordinatorEntity[TECHeatPumpCoordinator], BinarySensorEntity):
    """An alarm bit (discrete input) exposed as a binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TECHeatPumpCoordinator,
        config: dict[str, Any],
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)

        self._config = config

        self.entity_description = BinarySensorEntityDescription(
            key=config["unique_id"],
            translation_key=config.get("translation_key"),
            name=config.get("name"),
            device_class=config.get("device_class"),
        )

        self._attr_unique_id = f"{coordinator.entry.entry_id}_{config['unique_id']}"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        """Return True if the alarm bit is set."""
        value = self.coordinator.data.get(self.entity_description.key)
        return bool(value) if value is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device specific state attributes."""
        return {
            "address": self._config["address"],
            "device_id": self.coordinator.device_id,
            "function": self._config["function"],
        }
