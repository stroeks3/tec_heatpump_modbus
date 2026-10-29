"""Tests for the DHW water heater entity (pure logic, no HA instance)."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.water_heater import (
    STATE_ELECTRIC,
    STATE_HEAT_PUMP,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, STATE_OFF
from homeassistant.exceptions import ServiceValidationError

from custom_components.tec_heatpump_modbus.const import CONF_WATER_HEATER_WRITES, STATE_DHW
from custom_components.tec_heatpump_modbus.water_heater import TECHeatPumpWaterHeater

BASE = {"b4": 49.0, "st09": 53.0, "st15": 45.0, "st16": 75.0, "st10": 5.0, "st21": 58.0,
        "di5": True, "no8": False, "operational_state": 5, "dhw_restart_threshold": 48.0}


def _entity(writes=True, **data):
    c = MagicMock()
    c.entry.entry_id = "e"
    c.entry.options = {CONF_WATER_HEATER_WRITES: writes}
    c.option = lambda key, default: c.entry.options.get(key, default)
    c.device_id = 9
    c.device_info = {}
    c.data = {**BASE, **data}
    c.api_write_register = AsyncMock()
    c.write_coil = AsyncMock()
    c.async_request_refresh = AsyncMock()
    return TECHeatPumpWaterHeater(c), c


def test_reads_the_tank_and_setpoint_with_live_limits() -> None:
    wh, _ = _entity()
    assert wh.current_temperature == 49.0
    assert wh.target_temperature == 53.0
    assert (wh.min_temp, wh.max_temp) == (45.0, 75.0)


def test_limits_fall_back_when_st15_st16_do_not_read() -> None:
    wh, _ = _entity(st15=None, st16=None)
    assert (wh.min_temp, wh.max_temp) == (30.0, 80.0)


def test_operation_follows_the_dhw_switch_and_the_element() -> None:
    assert _entity()[0].current_operation == STATE_HEAT_PUMP
    assert _entity(no8=True)[0].current_operation == STATE_ELECTRIC
    assert _entity(di5=False)[0].current_operation == STATE_OFF
    assert _entity(di5=None)[0].current_operation is None


def test_electric_is_a_state_not_a_choice() -> None:
    wh, _ = _entity()
    assert STATE_ELECTRIC not in wh.operation_list
    assert wh.operation_list == [STATE_OFF, STATE_HEAT_PUMP]


def test_heating_attribute_tracks_the_dhw_state() -> None:
    assert _entity(operational_state=STATE_DHW)[0].extra_state_attributes["heating"] is True
    assert _entity()[0].extra_state_attributes["heating"] is False


def test_set_temperature_writes_st09_raw_and_clamps() -> None:
    wh, c = _entity()
    asyncio.run(wh.async_set_temperature(**{ATTR_TEMPERATURE: 55.0}))
    c.api_write_register.assert_awaited_once_with(address=79, value=550, device_id=9)
    c.api_write_register.reset_mock()
    asyncio.run(wh.async_set_temperature(**{ATTR_TEMPERATURE: 90.0}))
    c.api_write_register.assert_awaited_once_with(address=79, value=750, device_id=9)


def test_writes_off_hides_the_slider_and_refuses_the_write() -> None:
    wh, c = _entity(writes=False)
    assert not wh.supported_features & WaterHeaterEntityFeature.TARGET_TEMPERATURE
    assert wh.supported_features & WaterHeaterEntityFeature.ON_OFF
    with pytest.raises(ServiceValidationError):
        asyncio.run(wh.async_set_temperature(**{ATTR_TEMPERATURE: 55.0}))
    c.api_write_register.assert_not_awaited()


def test_on_off_writes_coil_2_regardless_of_the_write_option() -> None:
    wh, c = _entity(writes=False)
    asyncio.run(wh.async_turn_off())
    c.write_coil.assert_awaited_once_with(2, False, 9)
    asyncio.run(wh.async_turn_on())
    c.write_coil.assert_awaited_with(2, True, 9)
