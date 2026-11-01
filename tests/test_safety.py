"""Tests for the safety floors: the rules, the notices and the breach sensor."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from custom_components.tec_heatpump_modbus import TECHeatPumpCoordinator
from custom_components.tec_heatpump_modbus.binary_sensor import TECHeatPumpBinarySensor
from custom_components.tec_heatpump_modbus.const import (
    BINARY_SENSORS,
    CONF_SAFETY_REPAIRS,
    SAFETY_DEBOUNCE_S,
    SAFETY_FLOORS,
)
from custom_components.tec_heatpump_modbus.safety import (
    ISSUE_IDS,
    ISSUE_INVERTER,
    SEVERITY,
    evaluate,
)

OK = {"ev06": 23.0, "cm16": 30, "cm13": 30, "al_inv": False}


def _eval(data, now=0.0, below_since=None, **kw):
    below_since = {} if below_since is None else below_since
    return evaluate({**OK, **data}, now, below_since, **kw), below_since


# --- The rules --------------------------------------------------------------


def test_the_floors_are_the_safety_md_values() -> None:
    assert SAFETY_FLOORS == {"ev06": 23.0, "cm16": 30.0, "cm13": 30.0}
    assert SAFETY_DEBOUNCE_S == 300.0


def test_values_on_or_above_the_floor_are_fine() -> None:
    (active, unknown), below = _eval({})
    assert active == {} and unknown == set() and below == {}


def test_a_float_that_is_the_floor_up_to_rounding_is_not_a_breach() -> None:
    """EV06 arrives as raw * 0.1: 230 * 0.1 is 23.000000000000004, 229.9... can occur."""
    (active, _), below = _eval({"ev06": 22.99}, now=1000.0, below_since={"ev06": 0.0})
    assert active == {} and below == {}


def test_under_the_floor_waits_out_the_debounce() -> None:
    below = {}
    (active, _), below = _eval({"ev06": 15.0}, now=0.0, below_since=below)
    assert active == {} and below == {"ev06": 0.0}
    (active, _), below = _eval({"ev06": 15.0}, now=SAFETY_DEBOUNCE_S - 1, below_since=below)
    assert active == {}
    (active, _), below = _eval({"ev06": 15.0}, now=SAFETY_DEBOUNCE_S, below_since=below)
    assert list(active) == ["floor_ev06"]
    breach = active["floor_ev06"]
    assert (breach.value, breach.floor, breach.unit) == (15.0, 23.0, "%")
    assert breach.severity == "error"


def test_the_timer_starts_at_the_first_poll_and_not_at_each_poll() -> None:
    below = {}
    _eval({"cm16": 20}, now=10.0, below_since=below)
    _eval({"cm16": 21}, now=200.0, below_since=below)
    assert below == {"cm16": 10.0}


def test_back_above_the_floor_clears_at_once_and_resets_the_timer() -> None:
    below = {"cm16": 0.0}
    (active, _), below = _eval({"cm16": 30}, now=900.0, below_since=below)
    assert active == {} and below == {}


def test_a_stepwise_test_that_returns_in_time_never_reports() -> None:
    """Dropping a floor for a few minutes and restoring it must stay silent."""
    below = {}
    for now, value in ((0, 28), (60, 29), (120, 28), (200, 30)):
        (active, _), below = _eval({"cm16": value}, now=float(now), below_since=below)
        assert active == {}
    assert below == {}


def test_each_register_has_its_own_timer_and_severity() -> None:
    below = {}
    _eval({"cm13": 20}, now=0.0, below_since=below)
    (active, _), below = _eval({"cm13": 20, "cm16": 20}, now=400.0, below_since=below)
    assert list(active) == ["floor_cm13"]
    assert below == {"cm13": 0.0, "cm16": 400.0}
    assert SEVERITY["floor_cm13"] == "warning" and SEVERITY[ISSUE_INVERTER] == "critical"


def test_an_unreadable_register_is_unknown_and_leaves_the_timer_alone() -> None:
    below = {"ev06": 0.0}
    (active, unknown), below = _eval({"ev06": None}, now=400.0, below_since=below)
    assert active == {} and "floor_ev06" in unknown and below == {"ev06": 0.0}


def test_the_inverter_alarm_reports_at_once() -> None:
    (active, _), _ = _eval({"al_inv": True})
    assert list(active) == [ISSUE_INVERTER]
    assert active[ISSUE_INVERTER].severity == "critical"
    assert active[ISSUE_INVERTER].value is None


def test_an_unreadable_alarm_bit_is_unknown() -> None:
    (active, unknown), _ = _eval({"al_inv": None})
    assert active == {} and unknown == {ISSUE_INVERTER}


# --- The coordinator: notices -----------------------------------------------


def _coordinator(repairs=True):
    # No spec: hass and entry are set in the real __init__, which a spec'd mock
    # would refuse to have assigned.
    c = MagicMock()
    c.hass = MagicMock()
    c.entry.entry_id = "e1"
    c.option = lambda key, default: repairs if key == CONF_SAFETY_REPAIRS else default
    c._below_since = {}
    c._breached = set()
    c._issues_active = {}
    c._issues_synced = False
    c._sync_issues = lambda active: TECHeatPumpCoordinator._sync_issues(c, active)
    return c


def _poll(c, data, now):
    data = {**OK, **data}
    with patch("custom_components.tec_heatpump_modbus.time.monotonic", return_value=now):
        TECHeatPumpCoordinator._check_safety(c, data)
    return data


def _notices():
    return (
        patch("custom_components.tec_heatpump_modbus.ir.async_create_issue"),
        patch("custom_components.tec_heatpump_modbus.ir.async_delete_issue"),
    )


def test_a_breach_raises_one_notice_with_its_placeholders() -> None:
    c = _coordinator()
    p_create, p_delete = _notices()
    with p_create as create, p_delete:
        _poll(c, {"ev06": 15.0}, 0.0)
        assert create.call_count == 0
        data = _poll(c, {"ev06": 15.0}, 400.0)
    assert data["safety_breaches"] == ["ev06"]
    assert create.call_count == 1
    args, kwargs = create.call_args
    assert args[2] == "e1_floor_ev06"
    assert kwargs["translation_key"] == "floor_ev06"
    assert kwargs["translation_placeholders"] == {"value": "15", "floor": "23", "unit": "%"}
    assert kwargs["is_fixable"] is False


def test_a_notice_is_not_rewritten_on_every_poll() -> None:
    c = _coordinator()
    p_create, p_delete = _notices()
    with p_create as create, p_delete:
        _poll(c, {"ev06": 15.0}, 0.0)
        for now in (400.0, 405.0, 410.0, 415.0):
            _poll(c, {"ev06": 15.0}, now)
    assert create.call_count == 1


def test_a_notice_follows_the_value_when_it_changes() -> None:
    c = _coordinator()
    p_create, p_delete = _notices()
    with p_create as create, p_delete:
        _poll(c, {"ev06": 15.0}, 0.0)
        _poll(c, {"ev06": 15.0}, 400.0)
        _poll(c, {"ev06": 20.0}, 405.0)
    assert create.call_count == 2
    assert create.call_args.kwargs["translation_placeholders"]["value"] == "20"


def test_the_notice_goes_when_the_value_is_back() -> None:
    c = _coordinator()
    p_create, p_delete = _notices()
    with p_create, p_delete as delete:
        _poll(c, {"ev06": 15.0}, 0.0)
        _poll(c, {"ev06": 15.0}, 400.0)
        delete.reset_mock()
        data = _poll(c, {"ev06": 23.0}, 405.0)
    assert data["safety_breaches"] == []
    assert [call.args[2] for call in delete.call_args_list] == ["e1_floor_ev06"]


def test_the_first_poll_sweeps_notices_that_expired_while_unloaded() -> None:
    c = _coordinator()
    p_create, p_delete = _notices()
    with p_create, p_delete as delete:
        _poll(c, {}, 0.0)
    assert sorted(call.args[2] for call in delete.call_args_list) == sorted(
        f"e1_{i}" for i in ISSUE_IDS
    )
    # ...and only then: the polls after that do not touch the registry.
    with p_create, p_delete as delete:
        _poll(c, {}, 5.0)
    assert delete.call_count == 0


def test_an_unreadable_register_keeps_the_notice_up() -> None:
    c = _coordinator()
    p_create, p_delete = _notices()
    with p_create, p_delete as delete:
        _poll(c, {"ev06": 15.0}, 0.0)
        _poll(c, {"ev06": 15.0}, 400.0)
        delete.reset_mock()
        data = _poll(c, {"ev06": None}, 405.0)
    assert data["safety_breaches"] == ["ev06"]
    assert "e1_floor_ev06" not in [call.args[2] for call in delete.call_args_list]


def test_the_inverter_alarm_raises_a_critical_notice_and_clears() -> None:
    c = _coordinator()
    p_create, p_delete = _notices()
    with p_create as create, p_delete as delete:
        _poll(c, {"al_inv": True}, 0.0)
        assert create.call_args.kwargs["translation_key"] == "inverter_alarm"
        assert create.call_args.kwargs["severity"].value == "critical"
        delete.reset_mock()
        _poll(c, {"al_inv": False}, 5.0)
    assert "e1_inverter_alarm" in [call.args[2] for call in delete.call_args_list]


def test_with_the_option_off_no_notice_is_raised_but_the_sensor_still_works() -> None:
    c = _coordinator(repairs=False)
    p_create, p_delete = _notices()
    with p_create as create, p_delete:
        _poll(c, {"ev06": 15.0}, 0.0)
        data = _poll(c, {"ev06": 15.0}, 400.0)
    assert create.call_count == 0
    assert data["safety_breaches"] == ["ev06"]


def test_turning_the_option_off_takes_the_notices_down() -> None:
    c = _coordinator()
    p_create, p_delete = _notices()
    with p_create, p_delete as delete:
        _poll(c, {"ev06": 15.0}, 0.0)
        _poll(c, {"ev06": 15.0}, 400.0)
        c.option = lambda key, default: False if key == CONF_SAFETY_REPAIRS else default
        delete.reset_mock()
        _poll(c, {"ev06": 15.0}, 405.0)
    assert "e1_floor_ev06" in [call.args[2] for call in delete.call_args_list]


def test_two_entries_do_not_share_notices() -> None:
    a, b = _coordinator(), _coordinator()
    b.entry.entry_id = "e2"
    p_create, p_delete = _notices()
    with p_create as create, p_delete:
        for c in (a, b):
            _poll(c, {"ev06": 15.0}, 0.0)
            _poll(c, {"ev06": 15.0}, 400.0)
    assert sorted(call.args[2] for call in create.call_args_list) == [
        "e1_floor_ev06",
        "e2_floor_ev06",
    ]


# --- The sensor -------------------------------------------------------------


def _sensor(breaches):
    config = next(b for b in BINARY_SENSORS if b["unique_id"] == "safety_floor_breach")
    coordinator = MagicMock()
    coordinator.entry.entry_id = "e1"
    coordinator.device_id = 9
    coordinator.device_info = {}
    coordinator.data = {} if breaches is None else {"safety_breaches": breaches}
    return TECHeatPumpBinarySensor(coordinator, config)


def test_the_sensor_is_on_while_any_floor_is_breached() -> None:
    assert _sensor(["ev06"]).is_on is True
    assert _sensor([]).is_on is False


def test_the_sensor_is_unknown_before_the_first_judgement() -> None:
    assert _sensor(None).is_on is None


def test_the_sensor_names_the_registers_in_breach() -> None:
    attrs = _sensor(["cm16", "ev06"]).extra_state_attributes
    assert attrs["breaching_registers"] == ["cm16", "ev06"]
    assert attrs["floors"] == SAFETY_FLOORS
