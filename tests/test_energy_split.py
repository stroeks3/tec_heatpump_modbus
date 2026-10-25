"""Tests for the space-heating / DHW energy split and the per-mode daily COP."""
from __future__ import annotations

from collections import deque
from unittest.mock import MagicMock, patch

from custom_components.tec_heatpump_modbus import TECHeatPumpCoordinator
from custom_components.tec_heatpump_modbus.const import SENSORS, STATE_DHW

HEATING = 1


def _coordinator():
    """Only the state _add_calculated_values touches; the trackers are stubbed."""
    c = MagicMock(spec=TECHeatPumpCoordinator)
    c._energy = {
        "thermal_kj": 0.0, "elec_kj": 0.0, "day": None,
        "day_start_thermal_kj": 0.0, "day_start_elec_kj": 0.0,
        "space_thermal_kj": 0.0, "space_elec_kj": 0.0,
        "dhw_thermal_kj": 0.0, "dhw_elec_kj": 0.0,
        "day_start_space_thermal_kj": 0.0, "day_start_space_elec_kj": 0.0,
        "day_start_dhw_thermal_kj": 0.0, "day_start_dhw_elec_kj": 0.0,
    }
    c._bucket = "space"
    c._cop_samples = deque()
    c._last_poll_t = None
    c._last_store_save = 0.0
    c._store = MagicMock()
    c._storage_payload = lambda: {}
    c._daily_cop = TECHeatPumpCoordinator._daily_cop
    for name in ("_track_daily", "_track_tank", "_track_defrost", "_track_cycle", "_add_setpoints"):
        setattr(c, name, MagicMock())
    return c


def _poll(c, t, state, thermal_kw=6.0, elec_kw=2.0):
    """One poll at monotonic time t with flow/dT chosen to give thermal_kw."""
    data = {
        "b1": 30.0, "b2": 30.0 + thermal_kw / (1.0 * 1.163), "flow": 1.0,
        "compressor_power": elec_kw, "compressor": 50,
        "operational_state": state, "b6": 10.0, "b7": 30.0,
    }
    with patch("custom_components.tec_heatpump_modbus.time.monotonic", return_value=t), patch(
        "custom_components.tec_heatpump_modbus.dt_util.now"
    ) as now:
        now.return_value.date.return_value.isoformat.return_value = "2026-11-01"
        TECHeatPumpCoordinator._add_calculated_values(c, data)
    return data


def test_dhw_energy_lands_in_the_dhw_bucket() -> None:
    c = _coordinator()
    _poll(c, 0.0, STATE_DHW)
    data = _poll(c, 30.0, STATE_DHW)
    assert data["dhw_thermal_energy"] == 0.05
    assert data["dhw_compressor_energy"] == 0.02
    assert data["space_thermal_energy"] == 0.0
    assert data["space_compressor_energy"] == 0.0


def test_everything_else_is_space_heating() -> None:
    c = _coordinator()
    _poll(c, 0.0, HEATING)
    data = _poll(c, 30.0, HEATING)
    assert data["space_thermal_energy"] == 0.05
    assert data["dhw_thermal_energy"] == 0.0


def test_the_split_adds_up_to_the_total() -> None:
    c = _coordinator()
    t = 0.0
    for state in (HEATING, HEATING, STATE_DHW, STATE_DHW, HEATING):
        _poll(c, t, state)
        t += 30.0
    e = c._energy
    assert abs(e["space_elec_kj"] + e["dhw_elec_kj"] - e["elec_kj"]) < 1e-9
    assert abs(e["space_thermal_kj"] + e["dhw_thermal_kj"] - e["thermal_kj"]) < 1e-9


def test_a_failed_state_read_keeps_the_previous_bucket() -> None:
    c = _coordinator()
    _poll(c, 0.0, STATE_DHW)
    data = _poll(c, 30.0, None)
    assert data["dhw_compressor_energy"] == 0.02
    assert data["space_compressor_energy"] == 0.0


def test_per_mode_daily_cop_needs_its_own_tenth_of_a_kwh() -> None:
    c = _coordinator()
    t = 0.0
    # 2 kW for 180 s = 360 kJ = exactly the 0.1 kWh threshold, DHW only.
    for _ in range(7):
        _poll(c, t, STATE_DHW)
        t += 30.0
    data = _poll(c, t, STATE_DHW)
    assert data["cop_dhw_daily"] == 3.0
    assert data["cop_space_daily"] is None
    assert data["cop_daily"] == 3.0


def test_older_storage_without_the_split_still_loads() -> None:
    """An upgrade must not fail on a storage file that predates the split."""
    c = _coordinator()
    stored = {"thermal_kj": 1000.0, "elec_kj": 250.0, "day": "2026-10-31",
              "day_start_thermal_kj": 0.0, "day_start_elec_kj": 0.0}
    c._energy.update(stored)
    data = _poll(c, 0.0, HEATING)
    assert data["space_thermal_energy"] == 0.0
    assert data["thermal_energy"] == 0.28


def test_every_split_sensor_has_a_producer() -> None:
    keys = {
        s["unique_id"] for s in SENSORS
        if s["unique_id"] in {
            "space_thermal_energy", "space_compressor_energy",
            "dhw_thermal_energy", "dhw_compressor_energy",
            "cop_space_daily", "cop_dhw_daily",
        }
    }
    assert len(keys) == 6
    data = _poll(_coordinator(), 0.0, HEATING)
    for key in keys:
        assert key in data, f"{key} is defined but never produced"
