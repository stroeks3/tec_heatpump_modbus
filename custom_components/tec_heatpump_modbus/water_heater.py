"""The DHW tank as a Home Assistant water heater.

Nothing here is new to the unit: the tank sensor (B4), the DHW setpoint
(ST09), its limits (ST15/ST16), the DHW enable coil and the element
status bit were all exposed as separate entities already. This bundles
them into the one entity the thermostat card, voice assistants and the
Companion app already know how to handle.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.water_heater import (
    STATE_ELECTRIC,
    STATE_HEAT_PUMP,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_HALVES, STATE_OFF, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TECHeatPumpConfigEntry, TECHeatPumpCoordinator
from .const import CONF_WATER_HEATER_WRITES, DHW_TEMP_FALLBACK, DOMAIN, NUMBERS, STATE_DHW, SWITCHES

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0

ST09 = next(n for n in NUMBERS if n["unique_id"] == "st09")
DHW_COIL = next(s for s in SWITCHES if s["unique_id"] == "di5")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TECHeatPumpConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the water heater entity."""
    async_add_entities([TECHeatPumpWaterHeater(entry.runtime_data)])


class TECHeatPumpWaterHeater(CoordinatorEntity[TECHeatPumpCoordinator], WaterHeaterEntity):
    """The DHW tank."""

    _attr_has_entity_name = True
    _attr_translation_key = "dhw"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = PRECISION_HALVES
    _attr_target_temperature_step = 0.5
    # "electric" is a state the firmware puts the tank in when the element
    # takes over above the water limit; it cannot be requested, so it is not
    # in the list of selectable modes.
    _attr_operation_list = [STATE_OFF, STATE_HEAT_PUMP]

    def __init__(self, coordinator: TECHeatPumpCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_water_heater"
        self._attr_device_info = coordinator.device_info

    @property
    def _writes_enabled(self) -> bool:
        return self.coordinator.option(CONF_WATER_HEATER_WRITES, True)

    @property
    def supported_features(self) -> WaterHeaterEntityFeature:
        """On/off always; the setpoint only when writes are enabled.

        Without TARGET_TEMPERATURE the card hides the slider, which is the
        honest thing to show when another controller owns ST09.
        """
        features = WaterHeaterEntityFeature.ON_OFF
        if self._writes_enabled:
            features |= (
                WaterHeaterEntityFeature.TARGET_TEMPERATURE
                | WaterHeaterEntityFeature.OPERATION_MODE
            )
        return features

    @property
    def current_temperature(self) -> float | None:
        return self.coordinator.data.get("b4")

    @property
    def target_temperature(self) -> float | None:
        value = self.coordinator.data.get("st09")
        return round(value, 1) if value is not None else None

    @property
    def min_temp(self) -> float:
        value = self.coordinator.data.get("st15")
        return round(value, 1) if value is not None else DHW_TEMP_FALLBACK[0]

    @property
    def max_temp(self) -> float:
        value = self.coordinator.data.get("st16")
        return round(value, 1) if value is not None else DHW_TEMP_FALLBACK[1]

    @property
    def is_on(self) -> bool | None:
        enabled = self.coordinator.data.get("di5")
        return bool(enabled) if enabled is not None else None

    @property
    def current_operation(self) -> str | None:
        enabled = self.is_on
        if enabled is None:
            return None
        if not enabled:
            return STATE_OFF
        return STATE_ELECTRIC if self.coordinator.data.get("no8") else STATE_HEAT_PUMP

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {
            "heating": data.get("operational_state") == STATE_DHW,
            "element_on": bool(data.get("no8")) if data.get("no8") is not None else None,
            "water_limit": data.get("st21"),
            "restart_threshold": data.get("dhw_restart_threshold"),
            "writes_enabled": self._writes_enabled,
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Write ST09."""
        if not self._writes_enabled:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="writes_disabled"
            )
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        temperature = min(max(float(temperature), self.min_temp), self.max_temp)
        raw = round(temperature / ST09["scale"])
        await self.coordinator.api_write_register(
            address=ST09["address"], value=raw, device_id=self.coordinator.device_id
        )
        await self.coordinator.async_request_refresh()

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        if not self._writes_enabled:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="writes_disabled"
            )
        if operation_mode == STATE_OFF:
            await self.async_turn_off()
        else:
            await self.async_turn_on()

    async def _write_enable(self, value: bool) -> None:
        try:
            await self.coordinator.write_coil(
                DHW_COIL["address"], value, self.coordinator.device_id
            )
        except Exception as err:  # noqa: BLE001 - surface every write failure
            raise HomeAssistantError(f"Failed to switch DHW {'on' if value else 'off'}: {err}") from err
        finally:
            await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._write_enable(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._write_enable(False)
