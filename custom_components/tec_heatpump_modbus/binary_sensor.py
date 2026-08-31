"""Binary sensor platform for TEC Heat Pump Modbus (alarm bits)."""
from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BINARY_SENSORS,
    DHW_WATER_LIMIT_MARGIN,
    LOW_SUCTION_SUPERHEAT_THRESHOLD,
    PUMP_FLOW_FAULT_THRESHOLD,
)

# Raw value of UNIT_STATE_MAPPING's "DHW" entry, as read from IR 20.
DHW_STATE = 9
from . import TECHeatPumpCoordinator

_LOGGER = logging.getLogger(__name__)

# Entities only read from the coordinator's cached data; no direct I/O.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform from a config entry."""
    coordinator = entry.runtime_data

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
            entity_category=config.get("entity_category"),
            entity_registry_enabled_default=config.get("enabled_default", True),
        )

        self._attr_unique_id = f"{coordinator.entry.entry_id}_{config['unique_id']}"
        self._attr_device_info = coordinator.device_info
        self._delay_on = config.get("delay_on")
        self._calculated = config.get("calculated", False)
        self._raw_on_since: float | None = None

    def _raw_state(self) -> bool | None:
        """Return the undelayed condition, before any delay_on is applied."""
        if not self._calculated:
            value = self.coordinator.data.get(self.entity_description.key)
            return None if value is None else bool(value)

        if self.entity_description.key == "pump_flow_fault":
            commanded = self.coordinator.data.get("y3")
            flow = self.coordinator.data.get("flow")
            if commanded is None or flow is None:
                return None
            # Pump not asked to run: nothing to complain about.
            if commanded <= 0:
                return False
            return flow < PUMP_FLOW_FAULT_THRESHOLD

        if self.entity_description.key == "low_suction_superheat":
            freq = self.coordinator.data.get("compressor")
            superheat = self.coordinator.data.get("suction_superheat")
            if freq is None or superheat is None:
                return None
            # Compressor stopped: the reading is meaningless, not a fault.
            if not freq:
                return False
            return superheat < LOW_SUCTION_SUPERHEAT_THRESHOLD

        if self.entity_description.key == "dhw_water_limited":
            state = self.coordinator.data.get("operational_state")
            outlet = self.coordinator.data.get("b2")
            limit = self.coordinator.data.get("st21")
            if state is None or outlet is None or limit is None:
                return None
            # Only meaningful while heating hot water.
            if state != DHW_STATE:
                return False
            return outlet >= (limit - DHW_WATER_LIMIT_MARGIN)

        return None

    @property
    def is_on(self) -> bool | None:
        """Return True if the alarm condition holds.

        When the definition carries "delay_on", the condition must persist
        for that many seconds before it is reported as a problem. This
        filters the short transient the outlet-temperature alarms produce
        when the three-way valve switches back from the DHW circuit, and
        gives the pump time to build flow after it starts.
        """
        raw = self._raw_state()
        if raw is None:
            return None

        if not self._delay_on:
            return raw

        if not raw:
            self._raw_on_since = None
            return False

        now = time.monotonic()
        if self._raw_on_since is None:
            self._raw_on_since = now
        return (now - self._raw_on_since) >= self._delay_on

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device specific state attributes."""
        attrs: dict[str, Any] = {"device_id": self.coordinator.device_id}

        if self.entity_description.key == "pump_flow_fault":
            attrs["derived_from"] = "pump_pwm + water_flow"
            attrs["flow_threshold"] = PUMP_FLOW_FAULT_THRESHOLD
            attrs["pump_pwm"] = self.coordinator.data.get("y3")
            attrs["water_flow"] = self.coordinator.data.get("flow")
        elif self.entity_description.key == "low_suction_superheat":
            attrs["derived_from"] = "suction_superheat + compressor_frequency"
            attrs["superheat_threshold"] = LOW_SUCTION_SUPERHEAT_THRESHOLD
            attrs["suction_superheat"] = self.coordinator.data.get("suction_superheat")
            attrs["compressor_frequency"] = self.coordinator.data.get("compressor")
        elif self.entity_description.key == "dhw_water_limited":
            attrs["derived_from"] = "water_outlet + dhw_water_limit + operating_state"
            attrs["margin"] = DHW_WATER_LIMIT_MARGIN
            attrs["water_outlet"] = self.coordinator.data.get("b2")
            attrs["dhw_water_limit"] = self.coordinator.data.get("st21")
        else:
            attrs["address"] = self._config["address"]
            attrs["function"] = self._config["function"]

        if self._delay_on:
            attrs["delay_on_seconds"] = self._delay_on
            attrs["condition_met"] = self._raw_state()
        return attrs
