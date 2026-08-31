"""Tests for the slow holding-register cadence and the entity categories."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.const import EntityCategory

from custom_components.tec_heatpump_modbus.binary_sensor import TECHeatPumpBinarySensor
from custom_components.tec_heatpump_modbus.const import (
    BINARY_SENSORS,
    DHW_WATER_LIMIT_MARGIN,
    NUMBERS,
    SENSORS,
)
from custom_components.tec_heatpump_modbus import (
    SLOW_FUNCTIONS,
    SLOW_READ_INTERVAL_S,
)

LIMITED = next(c for c in BINARY_SENSORS if c["unique_id"] == "dhw_water_limited")
DHW_STATE = 9


# --- the slow cadence -----------------------------------------------------


def test_only_holding_registers_are_slow() -> None:
    """Input registers carry the live measurements and must stay fast.

    Function 3 is configuration; function 4 is what the machine is doing.
    Slowing the wrong one would make the whole integration lag.
    """
    assert SLOW_FUNCTIONS == frozenset({3})
    assert 4 not in SLOW_FUNCTIONS


def test_slow_interval_is_well_clear_of_the_poll_interval() -> None:
    """The saving only exists if the cadence is much slower than the poll."""
    assert SLOW_READ_INTERVAL_S >= 30.0


def test_every_writable_register_is_on_the_slow_group() -> None:
    """The point of the change: the 30 parameters are what make the block big.

    If a writable register ever lands on another function code, the slow
    cadence would silently stop covering it.
    """
    assert NUMBERS, "expected writable registers"
    assert all(n["function"] in SLOW_FUNCTIONS for n in NUMBERS)


def test_writes_force_a_slow_read() -> None:
    """Otherwise a changed setpoint would read stale for up to a minute."""
    from custom_components.tec_heatpump_modbus import TECHeatPumpCoordinator

    coordinator = MagicMock(spec=TECHeatPumpCoordinator)
    coordinator._slow_read_due = False
    TECHeatPumpCoordinator.force_slow_read(coordinator)
    assert coordinator._slow_read_due is True


# --- entity categories ----------------------------------------------------


def test_all_writable_parameters_are_config() -> None:
    assert all(n.get("entity_category") is EntityCategory.CONFIG for n in NUMBERS)


def test_primary_readings_stay_uncategorised() -> None:
    """These belong on the main card: they say what the machine is doing."""
    primary = {"b1", "b2", "hw", "compressor", "compressor_power", "operational_state"}
    for sensor in SENSORS:
        if sensor["unique_id"] in primary:
            assert sensor.get("entity_category") is None, sensor["unique_id"]


def test_unidentified_counters_are_diagnostic_and_off_by_default() -> None:
    for uid in ("unit_counter_ir16", "unit_counter_ir27"):
        cfg = next(s for s in SENSORS if s["unique_id"] == uid)
        assert cfg.get("entity_category") is EntityCategory.DIAGNOSTIC
        assert cfg.get("enabled_default") is False


def test_nothing_else_is_disabled_by_default() -> None:
    """Turning an entity off by default is a decision, not a default."""
    off = {s["unique_id"] for s in SENSORS if s.get("enabled_default") is False}
    assert off == {"unit_counter_ir16", "unit_counter_ir27"}


# --- the DHW ceiling indicator --------------------------------------------


def _limited_sensor(state, outlet, limit):
    coordinator = MagicMock()
    coordinator.entry.entry_id = "test_entry"
    coordinator.device_id = 9
    coordinator.device_info = {}
    coordinator.data = {
        "operational_state": state,
        "b2": outlet,
        "st21": limit,
    }
    return TECHeatPumpBinarySensor(coordinator, LIMITED)


def test_outlet_at_the_ceiling_during_dhw_is_limited() -> None:
    """Measured 2026-08-30: three stops, all at outlet 58.0-58.1 vs ST21 58.0."""
    assert _limited_sensor(DHW_STATE, 58.0, 58.0).is_on is True
    assert _limited_sensor(DHW_STATE, 58.1, 58.0).is_on is True


def test_outlet_well_below_the_ceiling_is_not_limited() -> None:
    assert _limited_sensor(DHW_STATE, 50.1, 58.0).is_on is False


def test_the_margin_catches_the_approach() -> None:
    """Just inside the margin counts; just outside it does not."""
    limit = 58.0
    assert _limited_sensor(DHW_STATE, limit - DHW_WATER_LIMIT_MARGIN, limit).is_on is True
    assert _limited_sensor(DHW_STATE, limit - DHW_WATER_LIMIT_MARGIN - 0.1, limit).is_on is False


def test_not_limited_outside_dhw() -> None:
    """A hot outlet while heating the house is not a DHW ceiling."""
    assert _limited_sensor(1, 58.5, 58.0).is_on is False  # Heating
    assert _limited_sensor(5, 58.5, 58.0).is_on is False  # Standby


def test_missing_readings_report_unknown() -> None:
    assert _limited_sensor(None, 58.0, 58.0).is_on is None
    assert _limited_sensor(DHW_STATE, None, 58.0).is_on is None
    # ST21 comes from the slow group, so it can be absent on the first polls.
    assert _limited_sensor(DHW_STATE, 58.0, None).is_on is None


def test_ceiling_indicator_is_not_a_problem_class() -> None:
    """This is designed behaviour, not a fault; it must not show up red."""
    assert LIMITED.get("device_class") is None
    assert LIMITED.get("entity_category") is EntityCategory.DIAGNOSTIC
