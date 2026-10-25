"""Tests for the DHW element runtime, the hot-tank tracker and rapid restarts."""
from __future__ import annotations

from collections import deque
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from custom_components.tec_heatpump_modbus import TECHeatPumpCoordinator
from custom_components.tec_heatpump_modbus.binary_sensor import TECHeatPumpBinarySensor
from custom_components.tec_heatpump_modbus.const import (
    BINARY_SENSORS,
    HOT_TANK_THRESHOLD,
    RAPID_RESTART_COUNT,
    RAPID_RESTART_WINDOW_S,
    SENSORS,
)

NOW = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)


def _coordinator(**daily):
    c = MagicMock(spec=TECHeatPumpCoordinator)
    c._daily = {
        "day": None,
        "starts": 0,
        "runtime_s": 0.0,
        "starts_yesterday": None,
        "runtime_yesterday": None,
        "heater_s": 0.0,
        "heater_yesterday": None,
        "defrosts": 0,
        "defrosts_yesterday": None,
    }
    c._daily.update(daily)
    c._was_running = None
    c._start_times = deque()
    c._last_hot = None
    c._store = MagicMock()
    c._storage_payload = lambda: {}
    c._publish_daily = lambda data: TECHeatPumpCoordinator._publish_daily(c, data)
    return c


def _run(c, polls, dt=30.0, today=date(2026, 10, 12)):
    """Feed dicts of readings through _track_daily on a fixed day."""
    data = {}
    with patch("custom_components.tec_heatpump_modbus.dt_util.now") as now:
        now.return_value.date.return_value = today
        for p in polls:
            data = dict(p)
            TECHeatPumpCoordinator._track_daily(c, data, dt)
    return data


# --- DHW element runtime ----------------------------------------------------


def test_element_runtime_counts_only_while_it_is_on() -> None:
    c = _coordinator()
    data = _run(c, [{"compressor": 0, "no8": False}] + [{"compressor": 0, "no8": True}] * 4)
    assert data["heater_runtime_today"] == 2.0


def test_element_is_counted_while_the_compressor_is_stopped() -> None:
    """The element takes over exactly when the compressor stops at ST21."""
    c = _coordinator()
    data = _run(c, [{"compressor": 0, "no8": True}] * 2)
    assert data["heater_runtime_today"] == 1.0


def test_element_is_counted_even_if_the_compressor_read_failed() -> None:
    c = _coordinator()
    data = _run(c, [{"no8": True}] * 2)
    assert data["heater_runtime_today"] == 1.0


def test_unreadable_element_adds_nothing() -> None:
    c = _coordinator()
    data = _run(c, [{"compressor": 0, "no8": None}] * 3)
    assert data["heater_runtime_today"] == 0.0


def test_element_runtime_rolls_into_yesterday() -> None:
    c = _coordinator()
    _run(c, [{"compressor": 0, "no8": True}] * 4, today=date(2026, 10, 11))
    data = _run(c, [{"compressor": 0, "no8": False}], today=date(2026, 10, 12))
    assert data["heater_runtime_yesterday"] == 2.0
    assert data["heater_runtime_today"] == 0.0


def test_element_gap_of_more_than_a_day_is_not_yesterday() -> None:
    c = _coordinator()
    _run(c, [{"compressor": 0, "no8": True}] * 4, today=date(2026, 10, 5))
    data = _run(c, [{"compressor": 0}], today=date(2026, 10, 12))
    assert data["heater_runtime_yesterday"] is None


# --- Hot tank ---------------------------------------------------------------


def _tank(c, tank, now=NOW):
    data = {"b4": tank}
    with patch("custom_components.tec_heatpump_modbus.dt_util.utcnow", return_value=now):
        TECHeatPumpCoordinator._track_tank(c, data)
    return data


def test_a_hot_tank_is_remembered() -> None:
    c = _coordinator()
    data = _tank(c, HOT_TANK_THRESHOLD)
    assert data["last_hot_tank"] == NOW
    assert data["days_since_hot_tank"] == 0.0


def test_days_since_grows_while_the_tank_stays_cooler() -> None:
    c = _coordinator()
    _tank(c, 62.0)
    data = _tank(c, 48.0, now=NOW + timedelta(days=3, hours=12))
    assert data["last_hot_tank"] == NOW
    assert data["days_since_hot_tank"] == 3.5


def test_below_threshold_never_counts() -> None:
    c = _coordinator()
    data = _tank(c, HOT_TANK_THRESHOLD - 0.1)
    assert data["last_hot_tank"] is None
    assert data["days_since_hot_tank"] is None


def test_unreadable_tank_does_not_erase_the_last_hot_run() -> None:
    c = _coordinator()
    _tank(c, 62.0)
    data = _tank(c, None, now=NOW + timedelta(days=1))
    assert data["last_hot_tank"] == NOW
    assert data["days_since_hot_tank"] == 1.0


def test_hot_tank_survives_a_restart() -> None:
    """The coordinator restores _last_hot from storage; the sensor must use it."""
    c = _coordinator()
    c._last_hot = NOW.isoformat()
    data = _tank(c, 45.0, now=NOW + timedelta(days=2))
    assert data["days_since_hot_tank"] == 2.0


# --- Rapid restarts ---------------------------------------------------------


def _clock(t):
    return patch("custom_components.tec_heatpump_modbus.time.monotonic", return_value=t)


def _starts(c, count, at=1000.0, gap=60.0):
    """Drive `count` stop/start pairs, `gap` seconds apart, from time `at`."""
    t = at
    for _ in range(count):
        with _clock(t):
            _run(c, [{"compressor": 0}])
        t += gap / 2
        with _clock(t):
            _run(c, [{"compressor": 50}])
        t += gap / 2
    return t


def test_starts_inside_the_window_are_counted() -> None:
    c = _coordinator()
    end = _starts(c, 3)
    with _clock(end):
        data = _run(c, [{"compressor": 50}])
    assert data["starts_in_window"] == 3


def test_old_starts_fall_out_of_the_window() -> None:
    c = _coordinator()
    _starts(c, 3)
    with _clock(1000.0 + RAPID_RESTART_WINDOW_S + 600):
        data = _run(c, [{"compressor": 50}])
    assert data["starts_in_window"] == 0


def test_a_run_in_progress_is_not_a_restart() -> None:
    c = _coordinator()
    with _clock(1000.0):
        data = _run(c, [{"compressor": 50}] * 5)
    assert data["starts_in_window"] == 0


def _rapid(starts):
    config = next(b for b in BINARY_SENSORS if b["unique_id"] == "rapid_restarts")
    coordinator = MagicMock()
    coordinator.entry.entry_id = "test_entry"
    coordinator.device_id = 9
    coordinator.device_info = {}
    coordinator.data = {"starts_in_window": starts}
    return TECHeatPumpBinarySensor(coordinator, config)


def test_threshold_is_the_safety_md_caution_line() -> None:
    """SAFETY.md: more than 3 starts in 30 minutes is the caution line."""
    assert RAPID_RESTART_COUNT == 4
    assert RAPID_RESTART_WINDOW_S == 1800.0
    assert _rapid(RAPID_RESTART_COUNT - 1).is_on is False
    assert _rapid(RAPID_RESTART_COUNT).is_on is True


def test_rapid_restarts_unknown_when_not_published() -> None:
    assert _rapid(None).is_on is None


# --- Wiring -----------------------------------------------------------------


def test_every_new_sensor_has_a_producer() -> None:
    """A sensor defined in const.py but never written would sit at unknown."""
    keys = {
        s["unique_id"]
        for s in SENSORS
        if s["unique_id"].startswith(("heater_runtime_", "days_since_", "last_hot_"))
    }
    assert keys == {
        "heater_runtime_today",
        "heater_runtime_yesterday",
        "last_hot_tank",
        "days_since_hot_tank",
    }
    c = _coordinator()
    data = _run(c, [{"compressor": 0, "no8": False}])
    with patch("custom_components.tec_heatpump_modbus.dt_util.utcnow", return_value=NOW):
        TECHeatPumpCoordinator._track_tank(c, data)
    for key in keys:
        assert key in data, f"{key} is defined but never produced"
