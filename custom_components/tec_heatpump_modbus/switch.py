"""Switch platform for TEC Heat Pump Modbus."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SWITCHES
from . import TECHeatPumpCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        TECHeatPumpSwitch(coordinator, switch_config)
        for switch_config in SWITCHES
    ]

    async_add_entities(entities)


class TECHeatPumpSwitch(CoordinatorEntity[TECHeatPumpCoordinator], SwitchEntity):
    """Represents a Modbus switch that fetches data from a coordinator."""
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TECHeatPumpCoordinator,
        config: dict[str, Any]
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)

        self._config = config

        self.entity_description = SwitchEntityDescription(
            key=config["unique_id"],
            translation_key=config.get("translation_key"),
            name=config.get("name"),
        )

        self._attr_unique_id = f"{coordinator.entry.entry_id}_{config['unique_id']}"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on, based on the coordinator's data."""
        value = self.coordinator.data.get(self.entity_description.key)
        return bool(value) if value is not None else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        _LOGGER.debug(f"Turning ON switch '{self.name}'")
        try:
            await self.coordinator.write_coil(
                self._config["address"],
                True,
                self.coordinator.device_id
            )
        except Exception as e:
            _LOGGER.error(f"Failed to turn on switch {self.name}: {e}")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        _LOGGER.debug(f"Turning OFF switch '{self.name}'")
        try:
            await self.coordinator.write_coil(
                self._config["address"],
                False,
                self.coordinator.device_id
            )
        except Exception as e:
            _LOGGER.error(f"Failed to turn off switch {self.name}: {e}")
        await self.coordinator.async_request_refresh()
