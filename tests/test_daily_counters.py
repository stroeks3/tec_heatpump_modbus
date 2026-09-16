"""Tests for the per-day compressor starts and runtime."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from custom_components.tec_heatpump_modbus import TECHeatPumpCoordinator


def _coordinator(day: str | None = None, **daily):
    """A coordinator with only the state _track_daily touches."""
    c = MagicMock(spec=TECHeatPumpCoordinator)
    c._daily = {
        "day": day,
        "starts": 0,
        "runtime_s": 0.0,
        "starts_yesterday": None,
        "runtime_yesterday": None,
    }
    c._daily.update(daily)
    c._was_running = None
    c._store = MagicMock()
    c._storage_payload = lambda: {}
    c._publish_daily = lambda data: TECHeatPumpCoordinator._publish_daily(c, data)
    return c


def _run(c, freqs, dt=30.0, today=date(2026, 9, 16)):
    """Feed compressor frequencies through _track_daily on a fixed day."""
    data = {}
    with patch(
        "custom_components.tec_heatpump_modbus.dt_util.now"
    ) as now:
        now.return_value.date.return_value = today
        for f in freqs:
            data = {} if f is None else {"compressor": f}
            TECHeatPumpCoordinator._track_daily(c, data, dt)
    return data


def test_a_run_is_one_start() -> None:
    c = _coordinator()
    data = _run(c, [0, 50, 50, 50, 0, 0])
    assert data["starts_today"] == 1
    # three polls of 30 s while running
    assert data["runtime_today"] == 1.5


def test_every_restart_counts_even_the_short_ones() -> None:
    """The cycle summary discards short runs; the start counter must not.

    Against the ST21 water ceiling the firmware produces one- and two-minute
    retries. Those are not cycles worth averaging, but a tank filled in six
    attempts is exactly what this sensor exists to make visible.
    """
    c = _coordinator()
    data = _run(c, [0, 50, 0, 50, 0, 50, 0])
    assert data["starts_today"] == 3


def test_a_running_compressor_at_first_poll_is_not_a_start() -> None:
    """On a fresh install we cannot tell a start from a run in progress."""
    c = _coordinator()
    data = _run(c, [50, 50, 50])
    assert data["starts_today"] == 0
    assert data["runtime_today"] == 1.5


def test_a_restart_mid_run_does_not_invent_a_start() -> None:
    """_was_running is restored from storage precisely for this."""
    c = _coordinator(day="2026-09-16", starts=2, runtime_s=600.0)
    c._was_running = True
    data = _run(c, [50, 50])
    assert data["starts_today"] == 2


def test_a_failed_read_is_not_a_stop() -> None:
    """A missing compressor register must not produce a phantom stop/start."""
    c = _coordinator()
    data = _run(c, [0, 50, None, None, 50, 50])
    assert data["starts_today"] == 1
    # the two polls without a reading add no runtime either
    assert data["runtime_today"] == 1.5


def test_midnight_rolls_today_into_yesterday() -> None:
    c = _coordinator()
    _run(c, [0, 50, 50, 0, 50, 0], today=date(2026, 9, 16))
    assert c._daily["starts"] == 2

    data = _run(c, [0], today=date(2026, 9, 17))
    assert data["starts_yesterday"] == 2
    assert data["runtime_yesterday"] == 1.5
    assert data["starts_today"] == 0
    assert data["runtime_today"] == 0.0


def test_a_gap_of_more_than_a_day_is_not_labelled_yesterday() -> None:
    """After a week offline, last Tuesday's total is not yesterday's."""
    c = _coordinator()
    _run(c, [0, 50, 50, 0], today=date(2026, 9, 16))
    data = _run(c, [0], today=date(2026, 9, 23))
    assert data["starts_yesterday"] is None
    assert data["runtime_yesterday"] is None


def test_runtime_does_not_survive_the_day_it_belongs_to() -> None:
    """Rollover resets today, it does not accumulate forever."""
    c = _coordinator()
    _run(c, [50] * 10, today=date(2026, 9, 16))
    data = _run(c, [50] * 2, today=date(2026, 9, 17))
    assert data["runtime_today"] == 1.0


def test_every_daily_sensor_has_a_producer() -> None:
    """A sensor defined in const.py but never written would sit at unknown."""
    from custom_components.tec_heatpump_modbus.const import SENSORS

    keys = [
        s["unique_id"]
        for s in SENSORS
        if s["unique_id"].startswith(("starts_", "runtime_"))
    ]
    assert keys, "the daily sensors disappeared from const.py"
    c = _coordinator()
    data = _run(c, [0, 50, 0])
    for key in keys:
        assert key in data, f"{key} is defined but never produced"
