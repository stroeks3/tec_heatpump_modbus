"""Tests for superheat gating and the Low Suction Superheat binary sensor."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.tec_heatpump_modbus.binary_sensor import TECHeatPumpBinarySensor
from custom_components.tec_heatpump_modbus.sensor import TECHeatPumpSensor
from custom_components.tec_heatpump_modbus.const import (
    BINARY_SENSORS,
    LOW_SUCTION_SUPERHEAT_THRESHOLD,
    SENSORS,
)

ALARM = next(c for c in BINARY_SENSORS if c["unique_id"] == "low_suction_superheat")
SUCTION = next(c for c in SENSORS if c["unique_id"] == "suction_superheat")
DISCHARGE = next(c for c in SENSORS if c["unique_id"] == "discharge_superheat")


def _coordinator(freq, superheat, discharge_superheat=5.0):
    coordinator = MagicMock()
    coordinator.entry.entry_id = "test_entry"
    coordinator.device_id = 9
    coordinator.device_info = {}
    coordinator.data = {
        "compressor": freq,
        "suction_superheat": superheat,
        "discharge_superheat": discharge_superheat,
    }
    return coordinator


@pytest.fixture
def frozen_clock(monkeypatch):
    now = {"t": 1000.0}
    monkeypatch.setattr(
        "custom_components.tec_heatpump_modbus.binary_sensor.time.monotonic",
        lambda: now["t"],
    )
    return now


# --- gating on the sensors themselves -------------------------------------


def test_superheat_is_unknown_while_the_compressor_is_stopped() -> None:
    """In standby the register still reports, but the number is meaningless.

    Measured on the unit: suction superheat drifts to about -4.8 K with the
    compressor off. Publishing that invites the wrong conclusion, so the
    sensor reports unknown instead.
    """
    coordinator = _coordinator(0, -4.8, -3.0)
    assert TECHeatPumpSensor(coordinator, SUCTION).native_value is None
    assert TECHeatPumpSensor(coordinator, DISCHARGE).native_value is None


def test_superheat_reports_normally_while_running() -> None:
    coordinator = _coordinator(50, 4.4, 23.0)
    assert TECHeatPumpSensor(coordinator, SUCTION).native_value == 4.4
    assert TECHeatPumpSensor(coordinator, DISCHARGE).native_value == 23.0


def test_superheat_is_unknown_when_the_frequency_is_missing() -> None:
    """A failed poll must not be read as a running compressor."""
    coordinator = _coordinator(None, 4.4)
    assert TECHeatPumpSensor(coordinator, SUCTION).native_value is None


def test_gating_does_not_leak_to_other_sensors() -> None:
    """Only entities carrying requires_compressor are gated."""
    gated = [s["unique_id"] for s in SENSORS if s.get("requires_compressor")]
    assert set(gated) == {"suction_superheat", "discharge_superheat"}


# --- the alarm ------------------------------------------------------------


def test_healthy_superheat_is_not_an_alarm() -> None:
    sensor = TECHeatPumpBinarySensor(_coordinator(50, 4.4), ALARM)
    assert sensor.is_on is False


def test_standby_drift_is_not_an_alarm() -> None:
    """-4.8 K in standby is the reading that must never raise an alarm."""
    sensor = TECHeatPumpBinarySensor(_coordinator(0, -4.8), ALARM)
    assert sensor.is_on is False


def test_brief_dip_does_not_alarm(frozen_clock) -> None:
    """Valve regulation dips below the threshold and recovers; that is normal.

    An 81-second dip must stay quiet, a 273-second one must not. Both were
    measured in a single DHW cycle on 2026-08-21.
    """
    coordinator = _coordinator(50, 0.4)
    sensor = TECHeatPumpBinarySensor(coordinator, ALARM)

    assert sensor.is_on is False
    frozen_clock["t"] += 81
    assert sensor.is_on is False

    coordinator.data["suction_superheat"] = 4.0
    assert sensor.is_on is False


def test_sustained_low_superheat_alarms(frozen_clock) -> None:
    coordinator = _coordinator(50, -0.2)
    sensor = TECHeatPumpBinarySensor(coordinator, ALARM)

    assert sensor.is_on is False
    frozen_clock["t"] += 119
    assert sensor.is_on is False

    frozen_clock["t"] += 2
    assert sensor.is_on is True


def test_bouncing_over_the_threshold_resets_the_timer(frozen_clock) -> None:
    """The reading oscillates; each excursion above the threshold restarts it.

    This is why the threshold pair matters. At 1.5 K the value bounced back
    over the line often enough that "continuously below" was never true and
    the alarm never fired at all.
    """
    coordinator = _coordinator(50, 1.2)
    sensor = TECHeatPumpBinarySensor(coordinator, ALARM)

    # 100 s below the threshold: not long enough yet.
    frozen_clock["t"] += 100
    assert sensor.is_on is False

    # One excursion above it discards those 100 s entirely.
    coordinator.data["suction_superheat"] = 2.4
    assert sensor.is_on is False

    # Back under. This read restarts the timer from zero, so the earlier 100 s
    # plus a little more is NOT enough - it needs a fresh 120 s.
    coordinator.data["suction_superheat"] = 1.2
    assert sensor.is_on is False
    frozen_clock["t"] += 25
    assert sensor.is_on is False

    frozen_clock["t"] += 96
    assert sensor.is_on is True


def test_missing_superheat_reports_unknown() -> None:
    sensor = TECHeatPumpBinarySensor(_coordinator(50, None), ALARM)
    assert sensor.is_on is None


def test_threshold_matches_the_tuned_value() -> None:
    """2.0 K and 120 s were arrived at empirically; guard them."""
    assert LOW_SUCTION_SUPERHEAT_THRESHOLD == 2.0
    assert ALARM["delay_on"] == 120
