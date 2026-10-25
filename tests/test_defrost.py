"""Tests for the defrost counter and last-defrost summary."""
from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from custom_components.tec_heatpump_modbus import TECHeatPumpCoordinator
from custom_components.tec_heatpump_modbus.const import SENSORS, STATE_DEFROST

NOW = datetime(2026, 12, 3, 6, 0, tzinfo=timezone.utc)
HEATING = 1


def _coordinator():
    c = MagicMock(spec=TECHeatPumpCoordinator)
    c._daily = {"day": None, "defrosts": 0, "defrosts_yesterday": None}
    c._defrost = None
    c._last_defrost = {}
    c._was_defrosting = None
    c._store = MagicMock()
    c._storage_payload = lambda: {}
    return c


def _run(c, polls, dt=30.0, now=NOW):
    """Feed dicts of readings through _track_defrost."""
    data = {}
    with patch("custom_components.tec_heatpump_modbus.dt_util.utcnow", return_value=now):
        for p in polls:
            data = dict(p)
            TECHeatPumpCoordinator._track_defrost(c, data, dt)
    return data


def _states(*codes, ambient=-1.5):
    return [{"operational_state": s, "t2": ambient} for s in codes]


def test_a_defrost_is_counted_once() -> None:
    c = _coordinator()
    data = _run(c, _states(HEATING, STATE_DEFROST, STATE_DEFROST, HEATING))
    assert data["defrosts_today"] == 1


def test_the_summary_freezes_when_the_defrost_ends() -> None:
    c = _coordinator()
    data = _run(c, _states(HEATING, STATE_DEFROST, STATE_DEFROST, STATE_DEFROST, HEATING))
    assert data["last_defrost"] == NOW
    assert data["last_defrost_duration"] == 1.5
    assert data["last_defrost_ambient"] == -1.5


def test_nothing_is_published_before_the_first_defrost() -> None:
    c = _coordinator()
    data = _run(c, _states(HEATING))
    assert data["last_defrost"] is None
    assert data["last_defrost_duration"] is None
    assert data["last_defrost_ambient"] is None


def test_a_unit_found_mid_defrost_at_startup_is_not_a_start() -> None:
    c = _coordinator()
    data = _run(c, _states(STATE_DEFROST, STATE_DEFROST, HEATING))
    assert data["defrosts_today"] == 0
    assert data["last_defrost"] is None


def test_a_failed_state_read_neither_starts_nor_ends_a_defrost() -> None:
    c = _coordinator()
    polls = _states(HEATING, STATE_DEFROST) + [{"t2": -1.5}] + _states(STATE_DEFROST, HEATING)
    data = _run(c, polls)
    assert data["defrosts_today"] == 1
    # The unknown poll added no time: two defrost polls of 30 s each.
    assert data["last_defrost_duration"] == 1.0


def test_ambient_is_sampled_at_the_start() -> None:
    c = _coordinator()
    polls = [
        {"operational_state": HEATING, "t2": 2.0},
        {"operational_state": STATE_DEFROST, "t2": -3.0},
        {"operational_state": STATE_DEFROST, "t2": 5.0},
        {"operational_state": HEATING, "t2": 5.0},
    ]
    data = _run(c, polls)
    assert data["last_defrost_ambient"] == -3.0


def test_the_summary_survives_a_restart() -> None:
    c = _coordinator()
    c._last_defrost = {"at": NOW.isoformat(), "duration": 4.5, "ambient": 0.5}
    data = _run(c, _states(HEATING))
    assert data["last_defrost"] == NOW
    assert data["last_defrost_duration"] == 4.5
    assert data["last_defrost_ambient"] == 0.5


def test_the_daily_rollover_moves_the_count_to_yesterday() -> None:
    """_track_daily owns the day boundary; it must roll the defrost count too."""
    from collections import deque

    c = _coordinator()
    c._daily.update({"day": "2026-12-03", "starts": 0, "runtime_s": 0.0,
                     "starts_yesterday": None, "runtime_yesterday": None,
                     "heater_s": 0.0, "heater_yesterday": None, "defrosts": 3})
    c._was_running = None
    c._start_times = deque()
    c._publish_daily = lambda data: TECHeatPumpCoordinator._publish_daily(c, data)
    with patch("custom_components.tec_heatpump_modbus.dt_util.now") as now:
        now.return_value.date.return_value = date(2026, 12, 4)
        TECHeatPumpCoordinator._track_daily(c, {"compressor": 0}, 30.0)
    data = _run(c, _states(HEATING))
    assert data["defrosts_yesterday"] == 3
    assert data["defrosts_today"] == 0


def test_every_defrost_sensor_has_a_producer() -> None:
    keys = {s["unique_id"] for s in SENSORS if "defrost" in s["unique_id"]}
    assert keys == {
        "defrosts_today", "defrosts_yesterday", "last_defrost",
        "last_defrost_duration", "last_defrost_ambient",
    }
    data = _run(_coordinator(), _states(HEATING))
    for key in keys:
        assert key in data, f"{key} is defined but never produced"
