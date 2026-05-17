"""Constants for the TEC Heat Pump Modbus integration."""

from homeassistant.components.button import ButtonEntityDescription
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

DOMAIN = "tec_heatpump_modbus"

CONF_NAME = "name"
CONF_DEVICE_ID = "device_id"
CONF_DELAY = "delay"
CONF_TIMEOUT = "timeout"

# Default values
DEFAULT_NAME = "TEC Heat Pump"
DEFAULT_PORT = 502
DEFAULT_DEVICE_ID = 9
DEFAULT_DELAY = 5
DEFAULT_TIMEOUT = 5

UNIT_STATE_MAPPING = { 1: "Heating", 2: "Cooling", 3: "Antifreeze", 4: "Defrost", 5: "Standby", 6: "Off", 7: "Starting", 8: "On", 9: "DHW" }
BINARY_STATE_MAPPING = { 1: "On", 0: "Off" }
BUTTONS: tuple[ButtonEntityDescription, ...] = (
    ButtonEntityDescription(
        key="refresh_data",
        translation_key="refresh_data",
        name="Refresh Data",
        icon="mdi:refresh",
    ),
)

SENSORS = [
    # Modbus Function Codes:
    # Function 1: Read Coils (read/write, 1 bit)
    # Function 2: Read Discrete Inputs (read-only, 1 bit)
    # Function 3: Read Holding Registers (read/write, 16 bit)
    # Function 4: Read Input Registers (read-only, 16 bit)
    #
    # Note: "scale" multiplies raw Modbus value to get display value (e.g. 0.1 means raw 250 -> 25.0°C)
    # Note: "min_value" and "max_value" are from TEC documentation (currently not enforced)
    
    # Holding Registers (writable) - Function 3
    { "unique_id": "st01", "translation_key": "st01", "name": "Cooling Setpoint", "address": 61, "data_type": "int16", "min_value": 0, "max_value": 600, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st02", "translation_key": "st02", "name": "Heating Setpoint", "address": 62, "data_type": "int16", "min_value": 0, "max_value": 600, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st03", "translation_key": "st03", "name": "Cooling dT", "address": 63, "data_type": "int16", "min_value": 10, "max_value": 100, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st04", "translation_key": "st04", "name": "Heating dT", "address": 64, "data_type": "int16", "min_value": 10, "max_value": 100, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st06", "translation_key": "st06", "name": "Heating Curve Slope", "address": 65, "data_type": "int16", "min_value": 0, "max_value": 30, "unit": "", "device_class": None, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st07", "translation_key": "st07", "name": "Aux Heat Start Ambient", "address": 66, "data_type": "int16", "min_value": -100, "max_value": 200, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st08", "translation_key": "st08", "name": "Cooling Curve Slope", "address": 67, "data_type": "int16", "min_value": 0, "max_value": 30, "unit": "", "device_class": None, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st09", "translation_key": "st09", "name": "DHW Setpoint", "address": 79, "data_type": "int16", "min_value": 0, "max_value": 800, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st10", "translation_key": "st10", "name": "DHW Hysteresis", "address": 80, "data_type": "int16", "min_value": 10, "max_value": 100, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st11", "translation_key": "st11", "name": "Cooling Setpoint Min", "address": 68, "data_type": "int16", "min_value": 0, "max_value": 600, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st12", "translation_key": "st12", "name": "Cooling Setpoint Max", "address": 69, "data_type": "int16", "min_value": 0, "max_value": 600, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st13", "translation_key": "st13", "name": "Heating Setpoint Min", "address": 70, "data_type": "int16", "min_value": 0, "max_value": 800, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st14", "translation_key": "st14", "name": "Heating Setpoint Max", "address": 71, "data_type": "int16", "min_value": 0, "max_value": 800, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st15", "translation_key": "st15", "name": "DHW Setpoint Min", "address": 72, "data_type": "int16", "min_value": 0, "max_value": 800, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st16", "translation_key": "st16", "name": "DHW Setpoint Max", "address": 73, "data_type": "int16", "min_value": 0, "max_value": 800, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st17", "translation_key": "st17", "name": "SG Heating Offset", "address": 74, "data_type": "int16", "min_value": 10, "max_value": 100, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st18", "translation_key": "st18", "name": "SG DHW Offset", "address": 75, "data_type": "int16", "min_value": 10, "max_value": 100, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st33", "translation_key": "st33", "name": "DHW Circ Pump Off Time", "address": 77, "data_type": "int16", "min_value": 0, "max_value": 180, "unit": "min", "device_class": SensorDeviceClass.DURATION, "writable": True, "function": 3, "scale": 1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "st34", "translation_key": "st34", "name": "DHW Circ Pump Run Time", "address": 78, "data_type": "int16", "min_value": 0, "max_value": 180, "unit": "min", "device_class": SensorDeviceClass.DURATION, "writable": True, "function": 3, "scale": 1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "room_temperature_setting", "translation_key": "room_temperature_setting", "name": "Room Setpoint", "address": 9, "data_type": "int16", "min_value": 0, "max_value": 500, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },

    # Compressor frequency limits (writable, Function 3)
    { "unique_id": "cm14", "translation_key": "cm14", "name": "Heating Rated Freq", "address": 115, "data_type": "int16", "min_value": 30, "max_value": 90, "unit": "Hz", "device_class": SensorDeviceClass.FREQUENCY, "writable": True, "function": 3, "scale": 1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "cm15", "translation_key": "cm15", "name": "Heating Max Freq", "address": 116, "data_type": "int16", "min_value": 30, "max_value": 95, "unit": "Hz", "device_class": SensorDeviceClass.FREQUENCY, "writable": True, "function": 3, "scale": 1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "cm17", "translation_key": "cm17", "name": "DHW Max Freq", "address": 117, "data_type": "int16", "min_value": 30, "max_value": 95, "unit": "Hz", "device_class": SensorDeviceClass.FREQUENCY, "writable": True, "function": 3, "scale": 1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "cm18", "translation_key": "cm18", "name": "DHW Min Freq", "address": 118, "data_type": "int16", "min_value": 20, "max_value": 60, "unit": "Hz", "device_class": SensorDeviceClass.FREQUENCY, "writable": True, "function": 3, "scale": 1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "cm16", "translation_key": "cm16", "name": "Heating Min Freq", "address": 121, "data_type": "int16", "min_value": 20, "max_value": 60, "unit": "Hz", "device_class": SensorDeviceClass.FREQUENCY, "writable": True, "function": 3, "scale": 1, "state_class": SensorStateClass.MEASUREMENT },

    # Indoor pump parameters (writable, Function 3)
    { "unique_id": "ev03", "translation_key": "ev03", "name": "Pump Target dT (Cooling)", "address": 18, "data_type": "int16", "min_value": 10, "max_value": 100, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "ev04", "translation_key": "ev04", "name": "Pump Target dT (Heating)", "address": 19, "data_type": "int16", "min_value": 10, "max_value": 100, "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "ev05", "translation_key": "ev05", "name": "Pump Max Speed", "address": 20, "data_type": "int16", "min_value": 200, "max_value": 1000, "unit": "%", "device_class": None, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "ev06", "translation_key": "ev06", "name": "Pump Min Speed", "address": 21, "data_type": "int16", "min_value": 150, "max_value": 500, "unit": "%", "device_class": None, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "ev07", "translation_key": "ev07", "name": "Pump Min Flow Alarm", "address": 22, "data_type": "int16", "min_value": 0, "max_value": 50, "unit": "m³/h", "device_class": None, "writable": True, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },

    # Input Registers (read-only) - Function 4
    { "unique_id": "b1", "translation_key": "b1", "name": "Water Inlet", "address": 1, "data_type": "int16", "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "function": 4, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "b2", "translation_key": "b2", "name": "Water Outlet", "address": 2, "data_type": "int16", "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "function": 4, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "t2", "translation_key": "t2", "name": "Ambient", "address": 3, "data_type": "int16", "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "function": 4, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "t4", "translation_key": "t4", "name": "Suction", "address": 4, "data_type": "int16", "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "function": 4, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "t3", "translation_key": "t3", "name": "Discharge", "address": 5, "data_type": "int16", "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "function": 4, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "b6", "translation_key": "b6", "name": "Low Pressure", "address": 6, "data_type": "int16", "unit": "bar", "device_class": SensorDeviceClass.PRESSURE, "function": 4, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "b7", "translation_key": "b7", "name": "High Pressure", "address": 7, "data_type": "int16", "unit": "bar", "device_class": SensorDeviceClass.PRESSURE, "function": 4, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "flow", "translation_key": "flow", "name": "Water Flow", "address": 8, "data_type": "int16", "unit": "m³/h", "device_class": None, "function": 4, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "room_temperature", "translation_key": "room_temperature", "name": "Room Temperature", "address": 9, "data_type": "int16", "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "function": 4, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "compressor", "translation_key": "compressor", "name": "Compressor Frequency", "address": 13, "data_type": "int16", "unit": "Hz", "device_class": SensorDeviceClass.FREQUENCY, "function": 4, "scale": 1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "y3", "translation_key": "y3", "name": "Pump PWM", "address": 14, "data_type": "int16", "unit": "%", "device_class": None, "function": 4, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "b4", "translation_key": "b4", "name": "DHW Tank", "address": 17, "data_type": "int16", "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "function": 4, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "operating_hours", "translation_key": "operating_hours", "name": "Operating Hours", "address": 18, "data_type": "int16", "unit": "h", "device_class": SensorDeviceClass.DURATION, "function": 4, "state_class": SensorStateClass.TOTAL },
    { "unique_id": "operational_state", "translation_key": "operational_state", "name": "Operating State", "address": 20, "data_type": "int16", "function": 4, "value_map": UNIT_STATE_MAPPING, "device_class": SensorDeviceClass.ENUM, "state_class": None },
    { "unique_id": "compressor_power", "translation_key": "compressor_power", "name": "Compressor Power", "address": 26, "data_type": "int16", "unit": "kW", "device_class": SensorDeviceClass.POWER, "function": 4, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    # Note: energy_consumed and energy_produced are commented out as the exact values and meanings are not yet known
    # { "unique_id": "energy_consumed", "translation_key": "energy_consumed", "name": "Total Energy Consumed", "address": 22, "data_type": "uint16", "unit": "kWh", "device_class": SensorDeviceClass.ENERGY, "function": 4, "scale": 1, "state_class": SensorStateClass.TOTAL_INCREASING },
    # { "unique_id": "energy_produced", "translation_key": "energy_produced", "name": "Total Energy Produced", "address": 23, "data_type": "uint16", "unit": "kWh", "device_class": SensorDeviceClass.ENERGY, "function": 4, "scale": 1, "state_class": SensorStateClass.TOTAL_INCREASING },
    
    # Discrete Inputs (read-only) - Function 2
    { "unique_id": "al01", "translation_key": "al01", "name": "Low Pressure Alarm", "address": 1, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "al02", "translation_key": "al02", "name": "High Pressure Alarm", "address": 2, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "al03", "translation_key": "al03", "name": "Low Outlet Temp Alarm", "address": 3, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "al05", "translation_key": "al05", "name": "High Outlet Temp Alarm", "address": 5, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "al17", "translation_key": "al17", "name": "Low Flow Alarm", "address": 6, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "al18", "translation_key": "al18", "name": "LP Alarm Count Exceeded", "address": 7, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "al19", "translation_key": "al19", "name": "HP Alarm Count Exceeded", "address": 8, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "secondary_pump", "translation_key": "secondary_pump", "name": "Secondary Pump", "address": 25, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "primary_pump", "translation_key": "primary_pump", "name": "Primary Pump", "address": 27, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "no4", "translation_key": "no4", "name": "AC Heater", "address": 32, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "d07", "translation_key": "d07", "name": "Crankcase Heater", "address": 33, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "no1", "translation_key": "no1", "name": "DHW Circ Pump", "address": 34, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "no8", "translation_key": "no8", "name": "DHW E-Heater", "address": 36, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "no6", "translation_key": "no6", "name": "Gas Boiler", "address": 39, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None }
]

REGISTER_TYPE_COIL = "coil"
REGISTER_TYPE_HOLDING = "holding"

SWITCHES = [
    { "unique_id": "di4", "translation_key": "di4", "name": "AC Switch", "address": 1, "register_type": REGISTER_TYPE_COIL, "function": 1 },
    { "unique_id": "di5", "translation_key": "di5", "name": "DHW Switch", "address": 2, "register_type": REGISTER_TYPE_COIL, "function": 1 },
    { "unique_id": "tr12", "translation_key": "tr12", "name": "SG Mode", "address": 3, "register_type": REGISTER_TYPE_COIL, "function": 1 }
]