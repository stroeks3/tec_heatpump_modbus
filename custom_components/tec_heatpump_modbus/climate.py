"""The heating/cooling side as a Home Assistant climate entity.

It regulates on water temperature, not room temperature, because that is
what the registers are. The current temperature is the water INLET
(return): that is what the unit regulates and restarts on, confirmed for
cooling on 2026-08-04 and for heating on 2026-10-26. A climate entity
pretending to control the room would be lying.

Season mode (HR 1, heating or cooling) is set on the PGDX panel and is
read-only over Modbus, so hvac_modes follows the season instead of
offering both.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_HALVES, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TECHeatPumpConfigEntry, TECHeatPumpCoordinator
from .const import (
    CONF_CLIMATE_WRITES,
    DOMAIN,
    MODE_COOLING,
    MODE_MAPPING,
    NUMBERS,
    STATE_COOLING,
    STATE_DEFROST,
    STATE_HEATING,
    STATE_OFF,
    STATE_STARTING,
    SWITCHES,
    UNIT_STATE_MAPPING,
)

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0

_NUMBER = {n["unique_id"]: n for n in NUMBERS}
AC_COIL = next(s for s in SWITCHES if s["unique_id"] == "di4")

# Operating state -> what the thermostat card shows. DHW, Standby, On and
# Antifreeze are all "idle" from the heating circuit's point of view; during
# a DHW cycle the water heater entity is the one that shows heating.
HVAC_ACTIONS = {
    STATE_HEATING: HVACAction.HEATING,
    STATE_COOLING: HVACAction.COOLING,
    STATE_DEFROST: HVACAction.DEFROSTING,
    STATE_STARTING: HVACAction.PREHEATING,
    STATE_OFF: HVACAction.OFF,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TECHeatPumpConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the climate entity."""
    async_add_entities([TECHeatPumpClimate(entry.runtime_data)])


class TECHeatPumpClimate(CoordinatorEntity[TECHeatPumpCoordinator], ClimateEntity):
    """Heating or cooling, by season."""

    _attr_has_entity_name = True
    _attr_translation_key = "heating"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = PRECISION_HALVES
    _attr_target_temperature_step = 0.5

    def __init__(self, coordinator: TECHeatPumpCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_climate"
        self._attr_device_info = coordinator.device_info

    # --- season -----------------------------------------------------------

    @property
    def _cooling_season(self) -> bool:
        return self.coordinator.data.get("mode") == MODE_COOLING

    @property
    def _season_mode(self) -> HVACMode:
        return HVACMode.COOL if self._cooling_season else HVACMode.HEAT

    def _reg(self, heating: str, cooling: str) -> float | None:
        value = self.coordinator.data.get(cooling if self._cooling_season else heating)
        return round(value, 1) if value is not None else None

    @property
    def _writes_enabled(self) -> bool:
        return self.coordinator.option(CONF_CLIMATE_WRITES, True)

    # --- state ------------------------------------------------------------

    @property
    def supported_features(self) -> ClimateEntityFeature:
        features = ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        if self._writes_enabled:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
        return features

    @property
    def hvac_modes(self) -> list[HVACMode]:
        return [HVACMode.OFF, self._season_mode]

    @property
    def hvac_mode(self) -> HVACMode | None:
        enabled = self.coordinator.data.get("di4")
        if enabled is None:
            return None
        return self._season_mode if enabled else HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        state = self.coordinator.data.get("operational_state")
        if state is None:
            return None
        return HVAC_ACTIONS.get(state, HVACAction.IDLE)

    @property
    def current_temperature(self) -> float | None:
        return self.coordinator.data.get("b1")

    @property
    def target_temperature(self) -> float | None:
        return self._reg("st02", "st01")

    @property
    def min_temp(self) -> float:
        value = self._reg("st13", "st11")
        if value is not None:
            return value
        return _NUMBER["st01" if self._cooling_season else "st02"]["min_value"] * 0.1

    @property
    def max_temp(self) -> float:
        value = self._reg("st14", "st12")
        if value is not None:
            return value
        return _NUMBER["st01" if self._cooling_season else "st02"]["max_value"] * 0.1

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        state = data.get("operational_state")
        return {
            "operating_state": UNIT_STATE_MAPPING.get(state, state),
            "season_mode": MODE_MAPPING.get(data.get("mode"), data.get("mode")),
            "water_outlet": data.get("b2"),
            "restart_threshold": data.get("restart_threshold"),
            "writes_enabled": self._writes_enabled,
        }

    # --- writes -----------------------------------------------------------

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Write ST02 (heating season) or ST01 (cooling season)."""
        if not self._writes_enabled:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="writes_disabled"
            )
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        number = _NUMBER["st01" if self._cooling_season else "st02"]
        temperature = min(max(float(temperature), self.min_temp), self.max_temp)
        raw = round(temperature / number["scale"])
        await self.coordinator.api_write_register(
            address=number["address"], value=raw, device_id=self.coordinator.device_id
        )
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._write_enable(False)
            return
        if hvac_mode != self._season_mode:
            # The season lives on the panel. Refusing loudly beats silently
            # enabling the opposite of what was asked.
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="wrong_season",
                translation_placeholders={"season": self._season_mode.value},
            )
        await self._write_enable(True)

    async def _write_enable(self, value: bool) -> None:
        try:
            await self.coordinator.write_coil(
                AC_COIL["address"], value, self.coordinator.device_id
            )
        except Exception as err:  # noqa: BLE001 - surface every write failure
            raise HomeAssistantError(f"Failed to switch heating {'on' if value else 'off'}: {err}") from err
        finally:
            await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        await self._write_enable(True)

    async def async_turn_off(self) -> None:
        await self._write_enable(False)
