"""Tests for the climate entity (pure logic, no HA instance)."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.climate import ClimateEntityFeature, HVACAction, HVACMode
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.exceptions import ServiceValidationError

from custom_components.tec_heatpump_modbus.climate import TECHeatPumpClimate
from custom_components.tec_heatpump_modbus.const import (
    CONF_CLIMATE_WRITES,
    MODE_COOLING,
    MODE_HEATING,
    STATE_DEFROST,
    STATE_DHW,
    STATE_HEATING,
    STATE_OFF,
    STATE_STANDBY,
    STATE_STARTING,
)

BASE = {"b1": 24.5, "b2": 28.0, "st02": 28.0, "st01": 18.0, "st13": 18.0, "st14": 40.0,
        "st11": 8.0, "st12": 30.0, "di4": True, "mode": MODE_HEATING,
        "operational_state": STATE_HEATING, "restart_threshold": 21.0}


def _entity(writes=True, **data):
    c = MagicMock()
    c.entry.entry_id = "e"
    c.entry.options = {CONF_CLIMATE_WRITES: writes}
    c.option = lambda key, default: c.entry.options.get(key, default)
    c.device_id = 9
    c.device_info = {}
    c.data = {**BASE, **data}
    c.api_write_register = AsyncMock()
    c.write_coil = AsyncMock()
    c.async_request_refresh = AsyncMock()
    return TECHeatPumpClimate(c), c


def test_heating_season_reads_st02_and_its_limits() -> None:
    cl, _ = _entity()
    assert cl.current_temperature == 24.5
    assert cl.target_temperature == 28.0
    assert (cl.min_temp, cl.max_temp) == (18.0, 40.0)
    assert cl.hvac_modes == [HVACMode.OFF, HVACMode.HEAT]
    assert cl.hvac_mode == HVACMode.HEAT


def test_cooling_season_reads_st01_and_its_limits() -> None:
    cl, _ = _entity(mode=MODE_COOLING)
    assert cl.target_temperature == 18.0
    assert (cl.min_temp, cl.max_temp) == (8.0, 30.0)
    assert cl.hvac_modes == [HVACMode.OFF, HVACMode.COOL]


def test_hvac_action_maps_the_operating_state() -> None:
    assert _entity()[0].hvac_action == HVACAction.HEATING
    assert _entity(operational_state=STATE_DEFROST)[0].hvac_action == HVACAction.DEFROSTING
    assert _entity(operational_state=STATE_STARTING)[0].hvac_action == HVACAction.PREHEATING
    assert _entity(operational_state=STATE_STANDBY)[0].hvac_action == HVACAction.IDLE
    # During DHW the heating circuit is idle; the water heater shows heating.
    assert _entity(operational_state=STATE_DHW)[0].hvac_action == HVACAction.IDLE
    assert _entity(operational_state=STATE_OFF)[0].hvac_action == HVACAction.OFF
    assert _entity(di4=False)[0].hvac_action == HVACAction.OFF
    assert _entity(operational_state=None)[0].hvac_action is None


def test_ac_switch_off_is_hvac_off() -> None:
    assert _entity(di4=False)[0].hvac_mode == HVACMode.OFF
    assert _entity(di4=None)[0].hvac_mode is None


def test_set_temperature_writes_the_seasons_register() -> None:
    cl, c = _entity()
    asyncio.run(cl.async_set_temperature(**{ATTR_TEMPERATURE: 30.5}))
    c.api_write_register.assert_awaited_once_with(address=62, value=305, device_id=9)
    cl, c = _entity(mode=MODE_COOLING)
    asyncio.run(cl.async_set_temperature(**{ATTR_TEMPERATURE: 19.0}))
    c.api_write_register.assert_awaited_once_with(address=61, value=190, device_id=9)


def test_set_temperature_clamps_to_the_unit_limits() -> None:
    cl, c = _entity()
    asyncio.run(cl.async_set_temperature(**{ATTR_TEMPERATURE: 55.0}))
    c.api_write_register.assert_awaited_once_with(address=62, value=400, device_id=9)


def test_writes_off_hides_the_slider_and_refuses_the_write() -> None:
    cl, c = _entity(writes=False)
    assert not cl.supported_features & ClimateEntityFeature.TARGET_TEMPERATURE
    assert cl.supported_features & ClimateEntityFeature.TURN_OFF
    with pytest.raises(ServiceValidationError):
        asyncio.run(cl.async_set_temperature(**{ATTR_TEMPERATURE: 30.0}))
    c.api_write_register.assert_not_awaited()


def test_hvac_mode_writes_coil_1() -> None:
    cl, c = _entity(writes=False)
    asyncio.run(cl.async_set_hvac_mode(HVACMode.OFF))
    c.write_coil.assert_awaited_once_with(1, False, 9)
    asyncio.run(cl.async_set_hvac_mode(HVACMode.HEAT))
    c.write_coil.assert_awaited_with(1, True, 9)


def test_the_wrong_season_is_refused_not_silently_mapped() -> None:
    cl, c = _entity()
    with pytest.raises(ServiceValidationError):
        asyncio.run(cl.async_set_hvac_mode(HVACMode.COOL))
    c.write_coil.assert_not_awaited()


def test_the_setpoint_stays_visible_as_an_attribute_when_writes_are_off() -> None:
    """HA hides `temperature` without TARGET_TEMPERATURE; the attribute must not."""
    assert _entity(writes=False)[0].extra_state_attributes["setpoint"] == 28.0
    assert _entity(writes=False, mode=MODE_COOLING)[0].extra_state_attributes["setpoint"] == 18.0
