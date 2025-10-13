"""Button platform for TEC Heat Pump Modbus."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, BUTTONS
from . import TECHeatPumpCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities(
        TECHeatPumpButton(coordinator, description) for description in BUTTONS
    )


class TECHeatPumpButton(CoordinatorEntity[TECHeatPumpCoordinator], ButtonEntity):
    """A button entity for the TEC heat pump."""
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TECHeatPumpCoordinator,
        description: ButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.entity_description = description
        
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Refresh button pressed, requesting data refresh.")
        await self.coordinator.async_request_refresh()