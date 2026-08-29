"""Tests for the derived Pump Flow Fault binary sensor."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.tec_heatpump_modbus.binary_sensor import TECHeatPumpBinarySensor
from custom_components.tec_heatpump_modbus.const import (
    BINARY_SENSORS,
    PUMP_FLOW_FAULT_THRESHOLD,
)

CONFIG = next(c for c in BINARY_SENSORS if c["unique_id"] == "pump_flow_fault")


def _sensor(pump_pwm, water_flow):
    """Build the entity over a coordinator holding just these two readings."""
    coordinator = MagicMock()
    coordinator.entry.entry_id = "test_entry"
    coordinator.device_id = 9
    coordinator.device_info = {}
    coordinator.data = {"y3": pump_pwm, "flow": water_flow}
    return TECHeatPumpBinarySensor(coordinator, CONFIG)


@pytest.fixture
def frozen_clock(monkeypatch):
    """Drive the entity's delay_on timer by hand."""
    now = {"t": 1000.0}
    monkeypatch.setattr(
        "custom_components.tec_heatpump_modbus.binary_sensor.time.monotonic",
        lambda: now["t"],
    )
    return now


def test_healthy_flow_while_running_is_not_a_fault() -> None:
    """Pump at 90% moving 1.5 m³/h is the normal running case."""
    assert _sensor(90.0, 1.5).is_on is False


def test_standby_flow_at_the_pwm_floor_is_not_a_fault() -> None:
    """23% PWM with 0.65 m³/h is normal standby, measured on the unit.

    This is the regression guard for the mistake this sensor replaced:
    IR 15 reads 0 in standby while the pump is genuinely circulating, so
    anything keyed on that register would fire here.
    """
    assert _sensor(23.0, 0.65).is_on is False


def test_pump_off_is_not_a_fault() -> None:
    """No flow is expected and fine when the pump is not being commanded."""
    assert _sensor(0.0, 0.0).is_on is False


def test_missing_readings_report_unknown() -> None:
    """A failed poll must not be read as a healthy pump."""
    assert _sensor(None, 0.0).is_on is None
    assert _sensor(90.0, None).is_on is None


def test_stalled_pump_needs_to_persist_before_it_alarms(frozen_clock) -> None:
    """Commanded but no flow: held for delay_on before it counts."""
    sensor = _sensor(90.0, 0.0)

    # Condition is true immediately, but the sensor waits.
    assert sensor.is_on is False
    frozen_clock["t"] += CONFIG["delay_on"] - 1
    assert sensor.is_on is False

    frozen_clock["t"] += 2
    assert sensor.is_on is True


def test_flow_returning_resets_the_timer(frozen_clock) -> None:
    """A dip that recovers must not accumulate towards the next one."""
    coordinator = MagicMock()
    coordinator.entry.entry_id = "test_entry"
    coordinator.device_id = 9
    coordinator.device_info = {}
    coordinator.data = {"y3": 90.0, "flow": 0.0}
    sensor = TECHeatPumpBinarySensor(coordinator, CONFIG)

    frozen_clock["t"] += CONFIG["delay_on"] - 5
    assert sensor.is_on is False

    # Flow recovers well clear of the threshold.
    coordinator.data["flow"] = 1.4
    assert sensor.is_on is False

    # It drops out again; the clock starts over rather than tripping at once.
    coordinator.data["flow"] = 0.0
    frozen_clock["t"] += 10
    assert sensor.is_on is False
    frozen_clock["t"] += CONFIG["delay_on"]
    assert sensor.is_on is True


def test_threshold_sits_between_stalled_and_the_pwm_floor() -> None:
    """The threshold must separate 'not moving' from the measured floor.

    0.0 m³/h with the pump off and 0.6-0.7 m³/h at the 23% floor were both
    measured on the unit; the threshold has to fall strictly between them.
    """
    assert 0.0 < PUMP_FLOW_FAULT_THRESHOLD < 0.6
