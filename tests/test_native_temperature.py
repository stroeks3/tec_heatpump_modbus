"""Climate and water heater use the native_ temperature API where Home Assistant has it.

Home Assistant 2026.11 deprecates temperature_unit, current_temperature and
target_temperature (removal in 2027.11) in favour of native_ forms. The
entities define whichever set their base class knows. The test harness may
run an older Home Assistant, so the newer base class is simulated by giving
the base class the native_ properties before the module is imported again.
"""
from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock

import pytest
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.water_heater import WaterHeaterEntity
from homeassistant.const import UnitOfTemperature

from custom_components.tec_heatpump_modbus.const import (
    CONF_CLIMATE_WRITES,
    CONF_WATER_HEATER_WRITES,
    MODE_HEATING,
    STATE_HEATING,
)

CLIMATE = "custom_components.tec_heatpump_modbus.climate"
WATER = "custom_components.tec_heatpump_modbus.water_heater"
LEGACY = ("current_temperature", "target_temperature")
NATIVE = ("native_current_temperature", "native_target_temperature")


def _coordinator(option_key, data):
    c = MagicMock()
    c.entry.entry_id = "e"
    c.entry.options = {option_key: True}
    c.option = lambda key, default: c.entry.options.get(key, default)
    c.device_info = {}
    c.data = data
    return c


CLIMATE_DATA = {"b1": 24.5, "st02": 28.0, "st01": 18.0, "mode": MODE_HEATING,
                "operational_state": STATE_HEATING, "di4": True}
WATER_DATA = {"b4": 49.0, "st09": 53.0, "di5": True, "no8": False}


@pytest.fixture
def simulate_new_home_assistant(monkeypatch):
    """Give both base classes the native_ properties, then reload the modules."""
    for base in (ClimateEntity, WaterHeaterEntity):
        for name in NATIVE:
            monkeypatch.setattr(base, name, property(lambda self: None), raising=False)
    yield
    monkeypatch.undo()
    for module in (CLIMATE, WATER):
        importlib.reload(sys.modules[module])


def _module(name):
    return importlib.reload(importlib.import_module(name))


def test_old_base_class_keeps_the_old_names() -> None:
    if hasattr(ClimateEntity, "native_current_temperature"):
        pytest.skip("this Home Assistant already has the native_ API")
    climate = _module(CLIMATE)
    water = _module(WATER)
    cl = climate.TECHeatPumpClimate(_coordinator(CONF_CLIMATE_WRITES, CLIMATE_DATA))
    wh = water.TECHeatPumpWaterHeater(_coordinator(CONF_WATER_HEATER_WRITES, WATER_DATA))
    assert cl._attr_temperature_unit == UnitOfTemperature.CELSIUS
    assert wh._attr_temperature_unit == UnitOfTemperature.CELSIUS
    assert (cl.current_temperature, cl.target_temperature) == (24.5, 28.0)
    assert (wh.current_temperature, wh.target_temperature) == (49.0, 53.0)
    for cls in (climate.TECHeatPumpClimate, water.TECHeatPumpWaterHeater):
        assert not any(name in cls.__dict__ for name in NATIVE)


def test_new_base_class_gets_only_the_native_names(simulate_new_home_assistant) -> None:
    climate = _module(CLIMATE)
    water = _module(WATER)
    cl = climate.TECHeatPumpClimate(_coordinator(CONF_CLIMATE_WRITES, CLIMATE_DATA))
    wh = water.TECHeatPumpWaterHeater(_coordinator(CONF_WATER_HEATER_WRITES, WATER_DATA))
    assert cl._attr_native_temperature_unit == UnitOfTemperature.CELSIUS
    assert wh._attr_native_temperature_unit == UnitOfTemperature.CELSIUS
    assert (cl.native_current_temperature, cl.native_target_temperature) == (24.5, 28.0)
    assert (wh.native_current_temperature, wh.native_target_temperature) == (49.0, 53.0)
    for cls in (climate.TECHeatPumpClimate, water.TECHeatPumpWaterHeater):
        # Defining the deprecated names is what makes Home Assistant warn.
        assert not any(name in cls.__dict__ for name in LEGACY)
        assert "_attr_temperature_unit" not in cls.__dict__


def test_setpoint_attribute_is_the_same_on_both_apis(simulate_new_home_assistant) -> None:
    climate = _module(CLIMATE)
    cl = climate.TECHeatPumpClimate(_coordinator(CONF_CLIMATE_WRITES, CLIMATE_DATA))
    assert cl.extra_state_attributes["setpoint"] == 28.0
