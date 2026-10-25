"""Tests for the active setpoint, its deviation and the restart thresholds."""
from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.tec_heatpump_modbus import TECHeatPumpCoordinator
from custom_components.tec_heatpump_modbus.const import SENSORS, STATE_DHW

HEATING, STANDBY = 1, 5
SEASON_HEATING, SEASON_COOLING = 0, 1

REGISTERS = {
    "st01": 18.0, "st03": 1.5, "st02": 28.0, "st04": 7.0, "st09": 53.0, "st10": 5.0,
    "b1": 24.5, "b4": 49.0,
}


def _run(**overrides):
    data = {**REGISTERS, "operational_state": HEATING, "mode": SEASON_HEATING, **overrides}
    TECHeatPumpCoordinator._add_setpoints(MagicMock(spec=TECHeatPumpCoordinator), data)
    return data


def test_heating_aims_at_st02_and_restarts_below_st02_minus_st04() -> None:
    data = _run()
    assert data["active_setpoint"] == 28.0
    assert data["setpoint_deviation"] == -3.5
    assert data["restart_threshold"] == 21.0


def test_cooling_aims_at_st01_and_restarts_above_st01_plus_st03() -> None:
    """The 2026-08-04 stuck-Standby case: ST01 + ST03 above the return."""
    data = _run(mode=SEASON_COOLING, b1=20.3)
    assert data["active_setpoint"] == 18.0
    assert data["setpoint_deviation"] == 2.3
    assert data["restart_threshold"] == 19.5


def test_dhw_aims_at_the_tank() -> None:
    data = _run(operational_state=STATE_DHW)
    assert data["active_setpoint"] == 53.0
    assert data["setpoint_deviation"] == -4.0


def test_dhw_restart_threshold_is_always_published() -> None:
    assert _run()["dhw_restart_threshold"] == 48.0
    assert _run(operational_state=STATE_DHW)["dhw_restart_threshold"] == 48.0


def test_standby_still_shows_what_the_unit_waits_for() -> None:
    data = _run(operational_state=STANDBY)
    assert data["active_setpoint"] == 28.0
    assert data["restart_threshold"] == 21.0


def test_missing_registers_give_unknown_not_a_crash() -> None:
    data = _run(st02=None, st04=None, b1=None)
    assert data["active_setpoint"] is None
    assert data["setpoint_deviation"] is None
    assert data["restart_threshold"] is None
    assert data["dhw_restart_threshold"] == 48.0


def test_every_setpoint_sensor_has_a_producer() -> None:
    keys = {
        s["unique_id"] for s in SENSORS
        if s["unique_id"] in {"active_setpoint", "setpoint_deviation",
                              "restart_threshold", "dhw_restart_threshold"}
    }
    assert len(keys) == 4
    data = _run()
    for key in keys:
        assert key in data
