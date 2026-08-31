"""Constants for the TEC Heat Pump Modbus integration."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.button import ButtonEntityDescription
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory

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
# HR 1. Read-only over Modbus; the mode itself is set on the PGDX panel at
# manufacturer level (unit must be OFF). Exposed so automations can tell heating
# season from cooling season without a trip to the panel.
# Named "Season Mode" rather than "Operating Mode" on purpose: it reads Cooling all
# summer regardless of what the unit is doing, and sitting next to an Operating
# State of Standby that was read as "it is cooling right now".
MODE_MAPPING = { 0: "Heating", 1: "Cooling" }
BUTTONS: tuple[ButtonEntityDescription, ...] = (
    ButtonEntityDescription(
        key="refresh_data",
        translation_key="refresh_data",
        name="Refresh Data",
        icon="mdi:refresh",
    ),
)

# Modbus Function Codes:
# Function 1: Read Coils (read/write, 1 bit)
# Function 2: Read Discrete Inputs (read-only, 1 bit)
# Function 3: Read Holding Registers (read/write, 16 bit)
# Function 4: Read Input Registers (read-only, 16 bit)
#
# Note: "scale" multiplies raw Modbus value to get display value (e.g. 0.1 means raw 213 -> 21.3°C).
#       Writes apply the inverse: display value / scale -> raw (21.3 -> 213).
# Note: "min_value" and "max_value" are RAW register values from TEC documentation;
#       number entities convert them to display units (min_value * scale).

NUMBERS = [
    # Holding Registers (writable) - Function 3
    { "unique_id": "st01", "translation_key": "st01", "name": "Cooling Setpoint", "address": 61, "data_type": "int16", "min_value": 0, "max_value": 600, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "st02", "translation_key": "st02", "name": "Heating Setpoint", "address": 62, "data_type": "int16", "min_value": 0, "max_value": 600, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "st03", "translation_key": "st03", "name": "Cooling dT", "address": 63, "data_type": "int16", "min_value": 10, "max_value": 100, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "st04", "translation_key": "st04", "name": "Heating dT", "address": 64, "data_type": "int16", "min_value": 10, "max_value": 100, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "st06", "translation_key": "st06", "name": "Heating Curve Slope", "address": 65, "data_type": "int16", "min_value": 0, "max_value": 30, "unit": None, "device_class": None, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "st07", "translation_key": "st07", "name": "Aux Heat Start Ambient", "address": 66, "data_type": "int16", "min_value": -100, "max_value": 200, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "st08", "translation_key": "st08", "name": "Cooling Curve Slope", "address": 67, "data_type": "int16", "min_value": 0, "max_value": 30, "unit": None, "device_class": None, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "st09", "translation_key": "st09", "name": "DHW Setpoint", "address": 79, "data_type": "int16", "min_value": 0, "max_value": 800, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "st10", "translation_key": "st10", "name": "DHW Hysteresis", "address": 80, "data_type": "int16", "min_value": 10, "max_value": 100, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "st11", "translation_key": "st11", "name": "Cooling Setpoint Min", "address": 68, "data_type": "int16", "min_value": 0, "max_value": 600, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "st12", "translation_key": "st12", "name": "Cooling Setpoint Max", "address": 69, "data_type": "int16", "min_value": 0, "max_value": 600, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "st13", "translation_key": "st13", "name": "Heating Setpoint Min", "address": 70, "data_type": "int16", "min_value": 0, "max_value": 800, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "st14", "translation_key": "st14", "name": "Heating Setpoint Max", "address": 71, "data_type": "int16", "min_value": 0, "max_value": 800, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "st15", "translation_key": "st15", "name": "DHW Setpoint Min", "address": 72, "data_type": "int16", "min_value": 0, "max_value": 800, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "st16", "translation_key": "st16", "name": "DHW Setpoint Max", "address": 73, "data_type": "int16", "min_value": 0, "max_value": 800, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "st17", "translation_key": "st17", "name": "SG Heating Offset", "address": 74, "data_type": "int16", "min_value": 10, "max_value": 100, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "st18", "translation_key": "st18", "name": "SG DHW Offset", "address": 75, "data_type": "int16", "min_value": 10, "max_value": 100, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "st33", "translation_key": "st33", "name": "DHW Circ Pump Off Time", "address": 77, "data_type": "int16", "min_value": 0, "max_value": 180, "unit": "min", "device_class": NumberDeviceClass.DURATION, "writable": True, "function": 3, "scale": 1 },
    { "unique_id": "st34", "translation_key": "st34", "name": "DHW Circ Pump Run Time", "address": 78, "data_type": "int16", "min_value": 0, "max_value": 180, "unit": "min", "device_class": NumberDeviceClass.DURATION, "writable": True, "function": 3, "scale": 1 },
    { "unique_id": "room_temperature_setting", "translation_key": "room_temperature_setting", "name": "Room Setpoint", "address": 9, "data_type": "int16", "min_value": 0, "max_value": 500, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },

    # Compressor frequency limits (writable, Function 3)
    { "unique_id": "cm14", "translation_key": "cm14", "name": "Heating Rated Freq", "address": 115, "data_type": "int16", "min_value": 30, "max_value": 90, "unit": "Hz", "device_class": NumberDeviceClass.FREQUENCY, "writable": True, "function": 3, "scale": 1 },
    { "unique_id": "cm15", "translation_key": "cm15", "name": "Heating Max Freq", "address": 116, "data_type": "int16", "min_value": 30, "max_value": 95, "unit": "Hz", "device_class": NumberDeviceClass.FREQUENCY, "writable": True, "function": 3, "scale": 1 },
    { "unique_id": "cm17", "translation_key": "cm17", "name": "DHW Max Freq", "address": 117, "data_type": "int16", "min_value": 30, "max_value": 95, "unit": "Hz", "device_class": NumberDeviceClass.FREQUENCY, "writable": True, "function": 3, "scale": 1 },
    { "unique_id": "cm18", "translation_key": "cm18", "name": "DHW Min Freq", "address": 118, "data_type": "int16", "min_value": 20, "max_value": 60, "unit": "Hz", "device_class": NumberDeviceClass.FREQUENCY, "writable": True, "function": 3, "scale": 1 },
    { "unique_id": "cm16", "translation_key": "cm16", "name": "Heating Min Freq", "address": 121, "data_type": "int16", "min_value": 20, "max_value": 60, "unit": "Hz", "device_class": NumberDeviceClass.FREQUENCY, "writable": True, "function": 3, "scale": 1 },

    # Indoor pump parameters (writable, Function 3)
    { "unique_id": "ev03", "translation_key": "ev03", "name": "Pump Target dT (Cooling)", "address": 18, "data_type": "int16", "min_value": 10, "max_value": 100, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "ev04", "translation_key": "ev04", "name": "Pump Target dT (Heating)", "address": 19, "data_type": "int16", "min_value": 10, "max_value": 100, "unit": "°C", "device_class": NumberDeviceClass.TEMPERATURE, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "ev05", "translation_key": "ev05", "name": "Pump Max Speed", "address": 20, "data_type": "int16", "min_value": 200, "max_value": 1000, "unit": "%", "device_class": None, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "ev06", "translation_key": "ev06", "name": "Pump Min Speed", "address": 21, "data_type": "int16", "min_value": 150, "max_value": 500, "unit": "%", "device_class": None, "writable": True, "function": 3, "scale": 0.1 },
    { "unique_id": "ev07", "translation_key": "ev07", "name": "Pump Min Flow Alarm", "address": 22, "data_type": "int16", "min_value": 0, "max_value": 50, "unit": "m³/h", "device_class": None, "writable": True, "function": 3, "scale": 0.1 },
]

SENSORS = [
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
    { "unique_id": "mode", "translation_key": "mode", "name": "Season Mode", "address": 1, "data_type": "int16", "function": 3, "value_map": MODE_MAPPING, "device_class": SensorDeviceClass.ENUM, "state_class": None },
    { "unique_id": "operational_state", "translation_key": "operational_state", "name": "Operating State", "address": 20, "data_type": "int16", "function": 4, "value_map": UNIT_STATE_MAPPING, "device_class": SensorDeviceClass.ENUM, "state_class": None },
    { "unique_id": "compressor_power", "translation_key": "compressor_power", "name": "Compressor Power", "address": 26, "data_type": "int16", "unit": "kW", "device_class": SensorDeviceClass.POWER, "function": 4, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    # Compressor current — finer resolution (0.1 A ≈ 23 W) than the power
    # register (0.1 kW), which is what makes the refined power estimate possible.
    { "unique_id": "comp_current_motor", "translation_key": "comp_current_motor", "name": "Compressor Current (Motor)", "address": 24, "data_type": "int16", "unit": "A", "device_class": SensorDeviceClass.CURRENT, "function": 4, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "comp_current_ac", "translation_key": "comp_current_ac", "name": "Compressor Current (AC)", "address": 25, "data_type": "int16", "unit": "A", "device_class": SensorDeviceClass.CURRENT, "function": 4, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    # Requested compressor speed (PID output). Differs from the actual speed
    # whenever the firmware throttles for pressure or discharge protection —
    # comparing the two makes that intervention visible.
    # Refrigerant circuit diagnostics. Superheat is a temperature DIFFERENCE, so it
    # deliberately carries no device_class: with SensorDeviceClass.TEMPERATURE, Home
    # Assistant would treat 3.5 K as an absolute temperature and convert it to -269.65 C
    # on installations configured in Celsius.
    # IR 15 = EC fan speed in volts. Shipped in 2026.08.04 as "Pump Speed Feedback",
    # which was wrong; corrected here after watching a full cycle instead of only
    # standby.
    #
    # It does not track the pump. On 2026-08-29 the pump ramped 23 -> 90% at 04:29:37
    # while IR 15 stayed 0; it rose to 280 at 04:31:38, seven seconds before the
    # compressor started, and dropped back to 0 at 05:36:43 the instant the compressor
    # stopped - a full minute before the pump stopped at 05:37:37. That is the fan's
    # duty cycle, not the pump's.
    #
    # The scale follows from the range. Values ran 280..325 and the floor is exactly
    # CN02 (HR 8, minimum fan speed) = 2.8 V, with CN01 (HR 7, maximum) = 3.7 V well
    # above the peak. So it is volts at scale 0.01, and 0 whenever the fan is off.
    { "unique_id": "fan_speed", "translation_key": "fan_speed", "name": "Fan Speed", "address": 15, "data_type": "int16", "unit": "V", "device_class": SensorDeviceClass.VOLTAGE, "function": 4, "scale": 0.01, "state_class": SensorStateClass.MEASUREMENT },
    # HR 100 = ST21, the absolute water-temperature ceiling the unit holds itself to
    # during DHW. It is what actually ends a DHW cycle: once the tank is warm enough
    # that reaching it would need water above this figure, the compressor stops and
    # retries after its minimum-off time. Measured 2026-08-22: two consecutive stops
    # both at an outlet of 58.1 against ST21 = 58.0.
    # Read-only here. The manual has it as a PGDX-panel parameter, and writing it is
    # the wrong lever anyway - discharge was already 101 C and high pressure 37 bar at
    # those stops.
    { "unique_id": "st21", "translation_key": "st21", "name": "DHW Water Limit", "address": 100, "data_type": "int16", "unit": "°C", "device_class": SensorDeviceClass.TEMPERATURE, "function": 3, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "eev_step", "translation_key": "eev_step", "name": "EEV Position", "address": 11, "data_type": "int16", "unit": "steps", "device_class": None, "function": 4, "scale": 1, "state_class": SensorStateClass.MEASUREMENT },
    # Both superheat registers carry "requires_compressor": with the compressor
    # stopped they keep reporting, but the number means nothing - suction superheat
    # drifts to around -4.8 K in standby. Reporting it anyway invites exactly the
    # wrong conclusion: on 2026-08-30 an unfiltered read of one DHW cycle gave 45%
    # of samples below 2.0 K with a minimum of -5.6 K, where the same cycle filtered
    # on a running compressor gave 6% and +0.2 K. A factor seven, in the alarming
    # direction. So the sensor reports unknown instead, and every graph, statistic
    # and automation gets it right without anyone having to know this.
    { "unique_id": "suction_superheat", "translation_key": "suction_superheat", "name": "Suction Superheat", "address": 12, "data_type": "int16", "unit": "K", "device_class": None, "function": 4, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT, "requires_compressor": True },
    { "unique_id": "discharge_superheat", "translation_key": "discharge_superheat", "name": "Discharge Superheat", "address": 28, "data_type": "int16", "unit": "K", "device_class": None, "function": 4, "scale": 0.1, "state_class": SensorStateClass.MEASUREMENT, "requires_compressor": True },
    { "unique_id": "freq_requested", "translation_key": "freq_requested", "name": "Compressor Frequency Requested", "address": 29, "data_type": "int16", "unit": "Hz", "device_class": SensorDeviceClass.FREQUENCY, "function": 4, "scale": 1, "state_class": SensorStateClass.MEASUREMENT },

    # Calculated sensors — derived in the coordinator from the readings above,
    # no Modbus register of their own.
    # Thermal power: water flow (m³/h) x dT (K) x 1.163 kWh/(m³·K).
    # Positive = heating the water, negative = cooling (extraction).
    { "unique_id": "thermal_power", "translation_key": "thermal_power", "name": "Thermal Power", "unit": "kW", "device_class": SensorDeviceClass.POWER, "state_class": SensorStateClass.MEASUREMENT, "calculated": True },
    # Live COP: |thermal power| / compressor electrical power. Only while the
    # compressor draws >= 0.5 kW (power register resolution is 0.1 kW);
    # otherwise unknown.
    { "unique_id": "cop", "translation_key": "cop", "name": "COP", "unit": None, "device_class": None, "state_class": SensorStateClass.MEASUREMENT, "calculated": True },
    # Energy-weighted average COP over the past hour — averages the register
    # quantization noise away, so it is also meaningful at low loads.
    { "unique_id": "cop_1h", "translation_key": "cop_1h", "name": "COP (1h Average)", "unit": None, "device_class": None, "state_class": SensorStateClass.MEASUREMENT, "calculated": True },
    # Energy-weighted COP since local midnight, from the persistent counters.
    { "unique_id": "cop_daily", "translation_key": "cop_daily", "name": "COP (Today)", "unit": None, "device_class": None, "state_class": SensorStateClass.MEASUREMENT, "calculated": True },
    # Cumulative energy counters (persist across restarts). Thermal counts
    # |heat| delivered to the water (heating and cooling both add).
    { "unique_id": "thermal_energy", "translation_key": "thermal_energy", "name": "Thermal Energy", "unit": "kWh", "device_class": SensorDeviceClass.ENERGY, "state_class": SensorStateClass.TOTAL_INCREASING, "calculated": True },
    { "unique_id": "compressor_energy", "translation_key": "compressor_energy", "name": "Compressor Energy", "unit": "kWh", "device_class": SensorDeviceClass.ENERGY, "state_class": SensorStateClass.TOTAL_INCREASING, "calculated": True },
    # IR 22 and IR 23 are the unit's own energy totals, confirmed 2026-08-21 by
    # comparing their steps against energy integrated independently over the same
    # 77-minute DHW cycle: +41 / +11 steps against 4.81 / 1.34 kWh, giving 3.73
    # against 3.59. At scale 1 the electrical counter would claim 11 kWh where 1.34
    # was measured, so the scale is 0.1 kWh per step.
    #
    # Two caveats that matter for how these are used:
    #   * They update roughly every 20 minutes of compressor runtime, not
    #     continuously. That cycle's last 19 minutes were still unbooked half an
    #     hour later. Never read them over a short window.
    #   * 16 bits at 0.1 kWh wraps every 6553.5 kWh, so the absolute readings are
    #     not lifetime totals. TOTAL_INCREASING handles a wrap as a meter reset,
    #     which is the behaviour we want.
    { "unique_id": "unit_thermal_energy", "translation_key": "unit_thermal_energy", "name": "Unit Thermal Energy Total", "address": 22, "data_type": "uint16", "unit": "kWh", "device_class": SensorDeviceClass.ENERGY, "function": 4, "scale": 0.1, "state_class": SensorStateClass.TOTAL_INCREASING },
    { "unique_id": "unit_electrical_energy", "translation_key": "unit_electrical_energy", "name": "Unit Electrical Energy Total", "address": 23, "data_type": "uint16", "unit": "kWh", "device_class": SensorDeviceClass.ENERGY, "function": 4, "scale": 0.1, "state_class": SensorStateClass.TOTAL_INCREASING },
    # Still unidentified. IR 16 held 52041 for an hour and a half of full load, so
    # it is not a counter - more likely a fixed code. IR 27 runs a sawtooth from 0
    # to roughly 34-41 and back over 4-7 minutes, but only during the last 20
    # minutes of a DHW cycle when discharge superheat is high, and the superheat
    # drops on every reset. Reads as a periodic valve or oil-return action.
    { "unique_id": "unit_counter_ir16", "translation_key": "unit_counter_ir16", "name": "Unit Counter IR16", "address": 16, "data_type": "uint16", "device_class": None, "function": 4, "scale": 1, "state_class": SensorStateClass.MEASUREMENT },
    { "unique_id": "unit_counter_ir27", "translation_key": "unit_counter_ir27", "name": "Unit Counter IR27", "address": 27, "data_type": "uint16", "device_class": None, "function": 4, "scale": 1, "state_class": SensorStateClass.MEASUREMENT },

    # Discrete Inputs (read-only) - Function 2
    { "unique_id": "secondary_pump", "translation_key": "secondary_pump", "name": "Secondary Pump", "address": 25, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "primary_pump", "translation_key": "primary_pump", "name": "Primary Pump", "address": 27, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "no4", "translation_key": "no4", "name": "AC Heater", "address": 32, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "d07", "translation_key": "d07", "name": "Crankcase Heater", "address": 33, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "no1", "translation_key": "no1", "name": "DHW Circ Pump", "address": 34, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "no8", "translation_key": "no8", "name": "DHW E-Heater", "address": 36, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    # Mirrors coil 1 (the AC master enable): it appeared the moment coil 1 went
    # TRUE again at 09:30:17 on 2026-08-21 and was absent for the whole period the
    # DHW blockade held DI4 off. Exposed so an automation writing that coil can
    # confirm the unit actually acted on it.
    { "unique_id": "di31", "translation_key": "di31", "name": "AC Enable Status", "address": 31, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None },
    { "unique_id": "no6", "translation_key": "no6", "name": "Gas Boiler", "address": 39, "data_type": "bool", "function": 2, "value_map": BINARY_STATE_MAPPING, "device_class": None, "state_class": None }
]

# Alarm bits (Discrete Inputs) exposed as binary sensors with
# device_class "problem" so they surface as real alarms in the UI,
# in notifications and in voice assistants.
# "delay_on" (seconds): the bit must stay set this long before the sensor
# reports a problem. The outlet-temperature alarms briefly trip when the
# three-way valve switches back from the DHW circuit and the sensor still
# sees hot tank water — a transient of well under a minute that is not a
# fault. Without this, every DHW cycle would fire a false alarm.
BINARY_SENSORS = [
    { "unique_id": "al01", "translation_key": "al01", "name": "Low Pressure Alarm", "address": 1, "data_type": "bool", "function": 2, "device_class": BinarySensorDeviceClass.PROBLEM },
    { "unique_id": "al02", "translation_key": "al02", "name": "High Pressure Alarm", "address": 2, "data_type": "bool", "function": 2, "device_class": BinarySensorDeviceClass.PROBLEM },
    { "unique_id": "al03", "translation_key": "al03", "name": "Low Outlet Temp Alarm", "address": 3, "data_type": "bool", "function": 2, "device_class": BinarySensorDeviceClass.PROBLEM, "delay_on": 120 },
    { "unique_id": "al05", "translation_key": "al05", "name": "High Outlet Temp Alarm", "address": 5, "data_type": "bool", "function": 2, "device_class": BinarySensorDeviceClass.PROBLEM, "delay_on": 120 },
    { "unique_id": "al17", "translation_key": "al17", "name": "Low Flow Alarm", "address": 6, "data_type": "bool", "function": 2, "device_class": BinarySensorDeviceClass.PROBLEM },
    { "unique_id": "al18", "translation_key": "al18", "name": "LP Alarm Count Exceeded", "address": 7, "data_type": "bool", "function": 2, "device_class": BinarySensorDeviceClass.PROBLEM },
    { "unique_id": "al19", "translation_key": "al19", "name": "HP Alarm Count Exceeded", "address": 8, "data_type": "bool", "function": 2, "device_class": BinarySensorDeviceClass.PROBLEM },
    # Latched inverter/IGBT failure alarm. Observed live on an RS07V/LF
    # during a real IGBT trip (stays 1 until the alarm is reset on the
    # panel or the unit is power-cycled).
    { "unique_id": "al_inv", "translation_key": "al_inv", "name": "Inverter Alarm", "address": 83, "data_type": "bool", "function": 2, "device_class": BinarySensorDeviceClass.PROBLEM },
    # Derived, not a register: the pump is being commanded but no water is moving.
    #
    # The unit's own AL17 covers this at its own threshold (EV07 x 0.8 for 5 s), but
    # EV07 defaults low and the alarm clears the moment flow creeps back over the
    # line, so a pump that is barely moving water never latches anything. This one
    # watches the pair directly and holds for a minute before it complains.
    #
    # Why it matters: below roughly 23% PWM the pump can stop moving water while the
    # controller still believes it is running. With the compressor on, no circulation
    # means no chiller-side flow to carry heat away from the inverter. That is the
    # documented contributor to this unit's 2026-05-13 IGBT trip.
    #
    # Threshold: 0.3 m³/h sits well under the 0.6-0.7 measured at the 23% floor and
    # well over the 0.0 seen with the pump off, so it separates "barely turning" from
    # "not moving water at all" without guessing at intermediate values.
    { "unique_id": "pump_flow_fault", "translation_key": "pump_flow_fault", "name": "Pump Flow Fault", "device_class": BinarySensorDeviceClass.PROBLEM, "calculated": True, "delay_on": 60 },
    # Derived: suction superheat has stayed too low for too long while running.
    #
    # Superheat near zero means the refrigerant leaving the evaporator is not fully
    # evaporated, so liquid is reaching the compressor. That dilutes the oil and in
    # the extreme causes slugging. Brief dips are ordinary valve regulation; a
    # sustained low reading is not.
    #
    # The threshold pair is empirical, and the obvious settings do not work. Two
    # minutes under 2.0 K was reached only after 3 minutes under 1.5 K never fired
    # at all, despite a 273-second dip to -0.2 K: the value oscillates and keeps
    # bouncing briefly back over 1.5, so "continuously below 1.5" is never true.
    # At 2 min / 2.0 K that dip does fire and an 81-second one does not, which is
    # the sensitivity we want.
    #
    # No compressor condition is needed here: the superheat sensor itself reports
    # unknown when the compressor is stopped (see "requires_compressor" above), and
    # unknown is not below the threshold.
    { "unique_id": "low_suction_superheat", "translation_key": "low_suction_superheat", "name": "Low Suction Superheat", "device_class": BinarySensorDeviceClass.PROBLEM, "calculated": True, "delay_on": 120 },
    # Derived, and NOT a problem: the DHW cycle is being held back by the water
    # temperature limit rather than by the tank setpoint.
    #
    # This is the single most confusing thing this unit does. A DHW cycle does not
    # end when the tank reaches ST09; it ends when the outlet reaches ST21 (58.0 C
    # here). Above that the compressor stops, waits out its minimum-off time,
    # retries, hits the same ceiling, and the electric heater fills the pauses. To
    # an owner it looks like unexplained short cycling well below setpoint.
    #
    # Measured 2026-08-30: three stops in one boost, all at an outlet of 58.0-58.1
    # against ST21 = 58.0, with the tank at 53.5 and a setpoint of 58. Watching
    # this sensor next to DHW Tank explains the whole pattern at a glance.
    #
    # Deliberately no device_class: this is normal, designed behaviour, not a fault.
    # The 0.5 K margin catches the approach rather than only the exact hit.
    { "unique_id": "dhw_water_limited", "translation_key": "dhw_water_limited", "name": "DHW Limited By Water Temp", "device_class": None, "calculated": True, "entity_category": EntityCategory.DIAGNOSTIC },
]

# How close the outlet must get to ST21 before the cycle counts as limited (K).
DHW_WATER_LIMIT_MARGIN = 0.5

# Below this flow, with the pump commanded on, water is not circulating (m³/h).
PUMP_FLOW_FAULT_THRESHOLD = 0.3

# Suction superheat below this (K) risks liquid returning to the compressor.
LOW_SUCTION_SUPERHEAT_THRESHOLD = 2.0

# --- Entity categories -----------------------------------------------------
# Without these, all 87 entities land in one undifferentiated list on the
# device page. Home Assistant renders CONFIG and DIAGNOSTIC in their own
# cards, which leaves the primary card showing what the machine is actually
# doing: temperatures, pressures, flow, state, power and COP.
#
# Every writable parameter is configuration by definition, so NUMBERS is
# stamped wholesale rather than listed.
_DIAGNOSTIC_SENSORS = frozenset({
    # Refrigerant circuit and drive internals: for troubleshooting, not for
    # telling whether the house is warm.
    "eev_step", "suction_superheat", "discharge_superheat",
    "comp_current_motor", "comp_current_ac", "freq_requested", "fan_speed",
    "y3", "operating_hours", "st21",
    # Reads 0.0 on this unit: there is no room sensor wired.
    "room_temperature",
    # Status bits from the discrete inputs.
    "secondary_pump", "primary_pump", "no4", "d07", "no1", "no8", "di31", "no6",
    # Unidentified, exposed for investigation only.
    "unit_counter_ir16", "unit_counter_ir27",
})

# Exposed so someone can help identify them, but off by default: they carry no
# usable meaning yet and would otherwise sit on every dashboard as noise.
_DISABLED_BY_DEFAULT = frozenset({"unit_counter_ir16", "unit_counter_ir27"})

for _entity in SENSORS:
    if _entity["unique_id"] in _DIAGNOSTIC_SENSORS:
        _entity.setdefault("entity_category", EntityCategory.DIAGNOSTIC)
    if _entity["unique_id"] in _DISABLED_BY_DEFAULT:
        _entity.setdefault("enabled_default", False)

for _entity in NUMBERS:
    _entity.setdefault("entity_category", EntityCategory.CONFIG)

del _entity

REGISTER_TYPE_COIL = "coil"
REGISTER_TYPE_HOLDING = "holding"

SWITCHES = [
    { "unique_id": "di4", "translation_key": "di4", "name": "AC Switch", "address": 1, "register_type": REGISTER_TYPE_COIL, "function": 1 },
    { "unique_id": "di5", "translation_key": "di5", "name": "DHW Switch", "address": 2, "register_type": REGISTER_TYPE_COIL, "function": 1 },
    { "unique_id": "tr12", "translation_key": "tr12", "name": "SG Mode", "address": 3, "register_type": REGISTER_TYPE_COIL, "function": 1 }
]
