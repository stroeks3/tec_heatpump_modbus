# Release Notes - v1.1.1

## Breaking Change: English entity IDs

Entity names are now consistently in English across all locales. Previously, users with a non-English Home Assistant locale (e.g. Dutch) received translated entity IDs such as `sensor.tec_heat_pump_temperatuur_koelmodus`. This made writing automations harder for anyone sharing templates across locales.

In this release the Dutch translations for sensor/switch/button names have been removed. The Home Assistant setup and options dialogs remain in Dutch for Dutch users — only the entity display names and IDs change.

### Migration

**Existing installations are not automatically renamed.** Home Assistant's entity registry preserves your current entity IDs.

If you want the new English entity IDs:

1. **Recommended:** Remove the integration via Settings → Devices & Services → TEC Heat Pump Modbus → Delete. Then add it again. New English entity IDs will be generated. History will be lost for these entities.
2. **Alternative:** Manually rename each entity via Settings → Devices & Services → TEC Heat Pump Modbus → click the entity → ID field. Preserves history.

### Examples

| Before (NL locale) | After (any locale) |
|---|---|
| `sensor.tec_heat_pump_temperatuur_koelmodus` | `sensor.tec_heat_pump_temperature_on_cooling_mode` |
| `sensor.tec_heat_pump_warmwater_temperatuur_instelling` | `sensor.tec_heat_pump_dhw_temperature_setup` |
| `sensor.tec_heat_pump_water_inlaattemperatuur` | `sensor.tec_heat_pump_water_inlet_temperature` |
| `switch.tec_heat_pump_warmwater_schakelaar` | `switch.tec_heat_pump_dhw_switch` |

---

# Release Notes - v1.1.0

## New Features

**Compressor frequency limit parameters (writable)**

Five new writable sensors expose the compressor frequency limits:

- `cm14` — Compressor Rated Heating Frequency (HR 115, Hz)
- `cm15` — Compressor Maximum Heating Frequency (HR 116, Hz)
- `cm16` — Compressor Minimum Heating Frequency (HR 121, Hz)
- `cm17` — Compressor Maximum DHW Frequency (HR 117, Hz)
- `cm18` — Compressor Minimum DHW Frequency (HR 118, Hz)

**Indoor pump parameters (writable)**

Five new writable sensors expose pump tuning parameters:

- `ev03` — Indoor Pump Target dT (Cooling) (HR 18, °C)
- `ev04` — Indoor Pump Target dT (Heating) (HR 19, °C)
- `ev05` — Indoor Pump Maximum Speed (HR 20, %)
- `ev06` — Indoor Pump Minimum Speed (HR 21, %)
- `ev07` — Indoor Pump Minimum Flow Alarm Threshold (HR 22, m³/h)

### Compatibility

- Existing automations continue to work unchanged.
- New sensors appear automatically after upgrade.
- Translations included for English (default) and Dutch.

---

# Release Notes - v1.0.0

## Initial Release

This is the first official release of the TEC Heat Pump Modbus integration for Home Assistant.

**Validation:**
- ✅ Home Assistant hassfest validation passed
- ✅ HACS validation passed

### Features

**Comprehensive Entity Support (70+ entities)**
- 20 writable settings (temperature setpoints, pump intervals, compensation factors)
- 18 read-only sensors (temperatures, pressures, flow, power consumption)
- 13 discrete inputs (alarms and status indicators)
- 3 switches (AC, DHW, SG Function)
- 1 refresh button

**Full Modbus Support**
- Efficient batch reading of Modbus registers
- Support for all 4 Modbus function codes
- Automatic data type conversion (int16, uint16, bool)
- Configurable scaling factors

**User-Friendly Configuration**
- Config flow for easy setup
- Configurable device ID, update interval, and timeout
- Optional custom device name
- Comprehensive error handling

**Translation Support**
- Full English translation (default)
- Dutch translation included
- Translation keys for all entities

**Write Service**
- Write values to writable registers via service call
- Automatic value scaling and validation
- Support for all 20 writable settings

### Technical Details

**Based on Official Documentation**
- Modbus register map from official TEC Heat Pump PDF manual
- Verified against wjtje/tec-heat-pump repository
- Accurate sensor names and units

**Code Quality**
- Clean, well-documented code
- No hardcoded values - fully configurable
- Proper Home Assistant conventions
- Comprehensive error handling and logging

### Installation

Install via HACS:
1. Add this repository to HACS as a custom repository
2. Install "TEC Heat Pump Modbus"
3. Restart Home Assistant
4. Add integration via Settings → Devices & Services

### Configuration

- **Host**: IP address of your TEC Heat Pump
- **Port**: Modbus TCP port (default: 502)
- **Device ID**: Modbus device/slave ID (default: 9)
- **Name**: Optional custom name for the device
- **Delay**: Update interval in seconds (default: 5)
- **Timeout**: Connection timeout in seconds (default: 5)

### Requirements

- Home Assistant 2023.1.0 or newer
- pymodbus >= 3.11.1
- TEC Heat Pump with Modbus TCP support

### Known Limitations

- Energy sensors (consumed/produced) are disabled pending verification of exact values and meanings
- Min/max values from documentation are not enforced in the UI

### Credits

- Based on official TEC Heat Pump documentation
- Inspired by wjtje/tec-heat-pump repository
- Developed for the Home Assistant community

---

For issues, questions, or contributions, visit: https://github.com/stroeks3/tec_heatpump_modbus

