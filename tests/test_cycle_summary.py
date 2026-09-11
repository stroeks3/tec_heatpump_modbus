"""Tests for the per-cycle summary and the compression ratio."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.tec_heatpump_modbus import (
    MIN_CYCLE_SECONDS,
    TECHeatPumpCoordinator,
)
from custom_components.tec_heatpump_modbus.const import SENSORS

CYCLE_KEYS = [s["unique_id"] for s in SENSORS if s["unique_id"].startswith("cycle_")]


def _coordinator():
    """A coordinator with only the state _track_cycle touches."""
    c = MagicMock(spec=TECHeatPumpCoordinator)
    c._cycle = None
    c._last_cycle = {}
    c._store = MagicMock()
    c._storage_payload = lambda: {}
    return c


def _run(c, samples, dt=30.0):
    """Feed samples through _track_cycle, returning the final data dict."""
    data = {}
    for s in samples:
        data = dict(s)
        TECHeatPumpCoordinator._track_cycle(c, data, dt)
    return data


def _sample(freq, sh=4.0, tank=45.0, discharge=80.0, hp=30.0, thermal=3.0, elec=1.0):
    return {
        "compressor": freq,
        "suction_superheat": sh,
        "b4": tank,
        "t3": discharge,
        "b7": hp,
        "thermal_power": thermal,
        "compressor_power": elec,
    }


def test_summary_appears_only_after_the_cycle_ends() -> None:
    """While running there is nothing to report yet."""
    c = _coordinator()
    data = _run(c, [_sample(50) for _ in range(20)])
    assert all(f"cycle_{k}" not in data for k in ("duration", "mean_superheat"))
    assert c._cycle is not None


def test_completed_cycle_is_summarised() -> None:
    c = _coordinator()
    samples = [_sample(50, sh=4.0, tank=45.0, discharge=80.0, hp=30.0) for _ in range(10)]
    samples += [_sample(50, sh=1.0, tank=50.0, discharge=100.0, hp=36.0) for _ in range(10)]
    samples += [_sample(0, tank=50.6)]
    data = _run(c, samples)

    # 20 running samples of 30 s
    assert data["cycle_duration"] == 10.0
    # ten at 4.0 K and ten at 1.0 K
    assert data["cycle_mean_superheat"] == 2.5
    assert data["cycle_low_superheat_pct"] == 50.0
    assert data["cycle_min_superheat"] == 1.0
    # peaks, not last values
    assert data["cycle_peak_discharge"] == 100.0
    assert data["cycle_peak_high_pressure"] == 36.0
    assert data["cycle_tank_rise"] == 5.6
    assert data["cycle_cop"] == 3.0


def test_short_run_is_not_summarised() -> None:
    """Retries against the ST21 ceiling are all tail and must not count.

    A 2-minute burst at the end of a DHW cycle sits entirely in the
    low-superheat regime; summarising it would report a far worse machine
    than the one that actually ran.
    """
    c = _coordinator()
    good = [_sample(50, sh=4.0) for _ in range(20)] + [_sample(0)]
    _run(c, good)
    before = dict(c._last_cycle)

    short = [_sample(50, sh=0.2) for _ in range(3)] + [_sample(0)]
    data = _run(c, short, dt=30.0)

    assert 3 * 30.0 < MIN_CYCLE_SECONDS
    assert c._last_cycle == before, "short burst overwrote the last real cycle"
    assert data["cycle_mean_superheat"] == before["mean_superheat"]


def test_summary_survives_until_the_next_cycle_completes() -> None:
    """Standby polls keep reporting the previous cycle, not unknown."""
    c = _coordinator()
    _run(c, [_sample(50) for _ in range(20)] + [_sample(0)])
    data = _run(c, [_sample(0) for _ in range(5)])
    assert data["cycle_duration"] == 10.0


def test_superheat_is_only_counted_while_running() -> None:
    """Standby readings are meaningless and must not enter the average.

    Measured on the unit across three standstills: -4.8, 1.4 and 15.4 K.
    Letting those in would make the average say nothing at all.
    """
    c = _coordinator()
    samples = [_sample(0, sh=-4.8) for _ in range(10)]
    samples += [_sample(50, sh=4.0) for _ in range(20)]
    samples += [_sample(0, sh=15.4)]
    data = _run(c, samples)
    assert data["cycle_mean_superheat"] == 4.0


def test_missing_readings_do_not_crash_or_poison_the_average() -> None:
    c = _coordinator()
    samples = []
    for i in range(20):
        s = _sample(50, sh=4.0)
        if i % 4 == 0:
            s["suction_superheat"] = None
            s["t3"] = None
            s["b7"] = None
        samples.append(s)
    samples.append(_sample(0))
    data = _run(c, samples)
    assert data["cycle_mean_superheat"] == 4.0
    assert data["cycle_duration"] == 10.0


def test_every_cycle_sensor_has_a_producer() -> None:
    """A sensor defined in const.py but never written would sit at unknown."""
    c = _coordinator()
    data = _run(c, [_sample(50) for _ in range(20)] + [_sample(0)])
    for key in CYCLE_KEYS:
        assert key in data, f"{key} is defined but never produced"


@pytest.mark.parametrize(
    "hp,lp,expected",
    [(36.0, 12.0, 3.0), (24.3, 10.8, 2.25), (36.0, 0, None), (None, 12.0, None), (36.0, None, None)],
)
def test_compression_ratio(hp, lp, expected) -> None:
    """Zero or missing suction pressure must not raise."""
    ratio = round(hp / lp, 2) if hp is not None and lp else None
    assert ratio == expected
