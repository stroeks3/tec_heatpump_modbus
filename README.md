# TEC Heat Pump Modbus - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/stroeks3/tec_heatpump_modbus.svg)](https://github.com/stroeks3/tec_heatpump_modbus/releases)
[![License](https://img.shields.io/github/license/stroeks3/tec_heatpump_modbus.svg)](LICENSE)

> **Disclaimer:** This is an unofficial integration created by the community, not by TEC (The Energy Combination). TEC does not provide support for it. This is a community project - use it entirely at your own risk. Developed and tested with the TEC RS07VLF 7kW (R32) heat pump.

A comprehensive Home Assistant integration for TEC (The Energy Combination) heat pumps using Modbus TCP protocol. Monitor and control your heat pump with 70+ entities for complete visibility and automation.

## Features

### 📊 Comprehensive Monitoring (70+ entities)
- **20 Writable Settings** - Temperature setpoints, pump intervals, compensation factors
- **18 Read-Only Sensors** - Temperatures, pressures, flow, power consumption, operating hours
- **13 Discrete Inputs** - Alarms and status indicators for all major components
- **3 Switches** - AC, DHW (Domestic Hot Water), and SG Function control
- **1 Refresh Button** - Manual data refresh on demand

### 🌍 Multi-Language Support
- Full English translation (default)
- Dutch (Nederlands) translation included
- Translation-ready architecture for additional languages

### ⚙️ Easy Configuration
- User-friendly setup via Home Assistant UI
- Configurable update interval and timeout
- Support for multiple heat pumps
- Optional custom device naming

### 🔧 Write Service
Control your heat pump by writing values to writable registers:
- `tec_heatpump_modbus.write_register` service
- Automatic value scaling and conversion
- Support for all 20 writable settings

### 🚀 Automation-Ready
All entities are standard Home Assistant entities, perfect for:
- Creating automations based on operating state
- Monitoring energy consumption
- Alerting on alarms or unusual conditions
- Optimizing heating/cooling schedules

## Prerequisites

- TEC heat pump with Modbus TCP support
- Modbus RTU to TCP/IP gateway or direct TCP connection
- Home Assistant 2023.1.0 or newer
- Network connectivity between Home Assistant and heat pump

## Installation

### Via HACS (Recommended)

1. **Add Custom Repository:**
   - Open HACS in Home Assistant
   - Go to `Integrations` → Click three dots (⋮) → `Custom repositories`
   - Add repository URL: `https://github.com/stroeks3/tec_heatpump_modbus`
   - Category: `Integration`
   - Click `ADD`

2. **Install Integration:**
   - Search for "TEC Heat Pump Modbus" in HACS
   - Click `Download`
   - Restart Home Assistant

### Manual Installation

1. Download the [latest release](https://github.com/stroeks3/tec_heatpump_modbus/releases)
2. Extract and copy the `custom_components/tec_heatpump_modbus` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Configuration

### Setup

1. Navigate to **Settings** → **Devices & Services**
2. Click **+ ADD INTEGRATION** and search for "**TEC Heat Pump Modbus**"
3. Enter the configuration details:

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| **Name** | Friendly name for your device | TEC Heat Pump | No |
| **Host** | IP address of Modbus gateway/device | - | Yes |
| **Port** | Modbus TCP port | 502 | Yes |
| **Device ID** | Modbus device/slave ID | 9 | Yes |
| **Delay** | Update interval in seconds | 5 | Yes |
| **Timeout** | Connection timeout in seconds | 5 | Yes |

4. Click **Submit** - the integration will discover all supported entities

### Multiple Heat Pumps

You can add multiple TEC heat pumps by configuring each with a unique name:
- Example: "TEC Heat Pump Living Room", "TEC Heat Pump Garage"
- Each device must have a unique Device ID or IP address

## Available Entities

### Sensors (38 total)

**Writable Settings (20)**
- Temperature setpoints (cooling, heating, DHW)
- Temperature differences
- Compensation factors
- DHW circulation pump timings
- Room temperature setting

**Read-Only Sensors (18)**
- Water inlet/outlet temperatures
- Outdoor ambient temperature
- Suction/discharge temperatures
- DHW tank temperature
- Low/high pressure side
- Water flow
- Compressor frequency & operating hours
- Compressor power consumption
- Unit operating state

### Discrete Inputs (13)
- Alarms: Low/high pressure, temperature, flow
- Status: Primary/secondary pump, heaters, gas boiler

### Switches (3)
- AC Switch (DI4)
- DHW Switch (DI5)
- SG Function (TR12)

### Buttons (1)
- Refresh Data

## Write Service

Control writable parameters using the `tec_heatpump_modbus.write_register` service:

```yaml
service: tec_heatpump_modbus.write_register
data:
  sensor: st01  # Sensor unique ID
  value: 25.5   # Value (automatically scaled)
```

**Writable Sensors:**
`st01`, `st02`, `st03`, `st04`, `st06`, `st07`, `st08`, `st09`, `st10`, `st11`, `st12`, `st13`, `st14`, `st15`, `st16`, `st17`, `st18`, `st33`, `st34`, `room_temperature_setting`

## Technical Details

**Modbus Implementation**
- Efficient batch reading of registers
- Support for all Modbus function codes (1-4)
- Automatic int16/uint16 conversion
- Configurable scaling factors

**Based On**
- Official TEC Heat Pump PDF manual
- Verified against wjtje/tec-heat-pump repository

## Troubleshooting

**Connection Issues**
- Verify IP address and port
- Check network connectivity
- Ensure Device ID matches heat pump configuration
- Try increasing timeout value

**Missing Entities**
- Check that your heat pump model supports all registers
- Some entities may not be available on all models
- Review Home Assistant logs for errors

**Data Not Updating**
- Check update interval (delay) setting
- Verify Modbus communication is stable
- Use Refresh Data button for manual update

## Contributing

Contributions are welcome! 

- 🐛 **Report bugs** via [GitHub Issues](https://github.com/stroeks3/tec_heatpump_modbus/issues)
- 💡 **Suggest features** via [GitHub Issues](https://github.com/stroeks3/tec_heatpump_modbus/issues)
- 🔧 **Submit pull requests** with improvements

## Credits

- Based on official TEC Heat Pump documentation
- Inspired by [wjtje/tec-heat-pump](https://github.com/wjtje/tec-heat-pump) repository
- Developed for the Home Assistant community

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation:** [GitHub Wiki](https://github.com/stroeks3/tec_heatpump_modbus/wiki) (coming soon)
- **Issues:** [GitHub Issues](https://github.com/stroeks3/tec_heatpump_modbus/issues)
- **Discussions:** [GitHub Discussions](https://github.com/stroeks3/tec_heatpump_modbus/discussions)

---

**⚠️ Remember:** This is an unofficial community integration. Use at your own risk.
