# TEC Heat Pump Modbus - Home Assistant Integration

![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg) ![GitHub release](https://img.shields.io/github/release/stroeks3/tec_heatpump_modbus.svg) ![License](https://img.shields.io/github/license/stroeks3/tec_heatpump_modbus.svg) ![IoT Class](https://img.shields.io/badge/IoT%20Class-Local%20Polling-blue.svg)

> **Disclaimer:** This is an unofficial integration created by the community, not by TEC (The Energy Combination). TEC does not provide support for it. This is a community project - use it entirely at your own risk. Developed and tested with the TEC RS07VLF 7kW (R32) heat pump.

A comprehensive Home Assistant integration for TEC (The Energy Combination) heat pumps using Modbus TCP protocol. Monitor and control your heat pump with 50+ entities for complete visibility and automation.

## Features

### 📊 Comprehensive Monitoring (50+ entities)

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

- TEC heat pump with Modbus support
- **Modbus RTU to TCP/IP WiFi module (REQUIRED - see setup below)**
- Home Assistant 2025.10.0 or newer
- Network connectivity between Home Assistant and heat pump

## 📡 WiFi Module Setup (Required)

**⚠️ CRITICAL: This integration cannot work without a WiFi module!**

A WiFi module (Modbus RTU to TCP/IP gateway) is essential to enable communication between Home Assistant and your TEC heat pump. The heat pump uses Modbus RTU natively, so you need a converter to bridge to TCP/IP for network connectivity.

### Recommended Hardware

**Tested & Verified:**
- **[USR-W610 Modbus RTU to WiFi Converter](https://aliexpress.com/item/1005006115167929.html)**
  - ✅ Easy setup - working within minutes
  - ✅ Used for building and testing this integration
  - ✅ Reliable performance
  - ⚠️ **Important:** Make sure to choose the correct power adapter for your region when ordering

### Wiring Instructions

**Before connecting, always consult your TEC heat pump's official manual!**

1. **Locate Modbus terminals** on your TEC heat pump control board
2. **Reference official wiring diagrams:**
   - Check your TEC heat pump installation manual
   - Example reference: [VVS-Eksperten Installation Manual](https://www.vvs-eksperten.dk/amfile/file/download/file/371/product/5230/)

3. **Typical wiring connections:**
   - Connect WiFi module to heat pump's Modbus RTU terminals
   - Ensure correct polarity: **A+** and **B-** terminals
   - Use shielded twisted pair cable for best results (recommended but not required)
   - Keep cable length under 10 meters when possible

4. **Power requirements:**
   - Power the WiFi module according to manufacturer specifications
   - Ensure stable power supply to avoid communication dropouts

### WiFi Module Configuration

1. **Initial Setup:**
   - Power up the WiFi module
   - Connect to the module's configuration interface (see manufacturer instructions)
   - Connect module to your local WiFi network

2. **Modbus Settings (Critical):**
   - **Protocol:** Modbus TCP/RTU Gateway mode
   - **Baud Rate:** 9600
   - **Data Bits:** 8
   - **Parity:** Even
   - **Stop Bits:** 2
   - **TCP Port:** **502** (standard Modbus TCP port)

3. **Network Settings:**
   - Note the module's **IP address** (you'll need this for Home Assistant)
   - Configure static IP or DHCP reservation (recommended for stability)
   - Ensure the module is on the same network as Home Assistant

4. **Verification:**
   - Confirm the module can communicate with the heat pump
   - Test basic connectivity using manufacturer's tools (if available)
   - Note the IP address for the integration setup

Once configured, use the module's IP address when setting up the Home Assistant integration.

## Installation

### Via HACS (Recommended)

1. **Add Custom Repository:**
   - Open HACS in Home Assistant
   - Go to **Integrations** → Click three dots **(⋮)** → **Custom repositories**
   - Add repository URL: `https://github.com/stroeks3/tec_heatpump_modbus`
   - Category: **Integration**
   - Click **ADD**

2. **Install Integration:**
   - Search for "TEC Heat Pump Modbus" in HACS
   - Click **Download**
   - Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Extract and copy the `custom_components/tec_heatpump_modbus` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Configuration

### Setup

1. Navigate to **Settings** → **Devices & Services**
2. Click **+ ADD INTEGRATION** and search for "TEC Heat Pump Modbus"
3. Enter the configuration details:

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| **Name** | Friendly name for your device | TEC Heat Pump | No |
| **Host** | IP address of Modbus gateway/WiFi module | - | Yes |
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

#### Writable Settings (20)

- Temperature setpoints (cooling, heating, DHW)
- Temperature differences
- Compensation factors
- DHW circulation pump timings
- Room temperature setting

#### Read-Only Sensors (18)

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

- **Alarms:** Low/high pressure, temperature, flow
- **Status:** Primary/secondary pump, heaters, gas boiler

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

**Writable Sensors:** `st01`, `st02`, `st03`, `st04`, `st06`, `st07`, `st08`, `st09`, `st10`, `st11`, `st12`, `st13`, `st14`, `st15`, `st16`, `st17`, `st18`, `st33`, `st34`, `room_temperature_setting`

## Technical Details

### Modbus Implementation

- Efficient batch reading of registers
- Support for all Modbus function codes (1-4)
- Automatic int16/uint16 conversion
- Configurable scaling factors

### Based On

- Official TEC Heat Pump PDF manual
- Verified against [wjtje/tec-heat-pump](https://github.com/wjtje/tec-heat-pump) repository

## Troubleshooting

### Connection Issues

- ✅ Verify IP address and port of WiFi module
- ✅ Check network connectivity between Home Assistant and WiFi module
- ✅ Ensure Device ID matches heat pump configuration (typically 9)
- ✅ Verify WiFi module is powered and connected to network
- ✅ Check WiFi module Modbus settings (baud rate, protocol)
- ✅ Try increasing timeout value in integration settings
- ✅ Restart WiFi module and check LED indicators

### Missing Entities

- Check that your heat pump model supports all registers
- Some entities may not be available on all models
- Review Home Assistant logs for errors

### Data Not Updating

- Check update interval (delay) setting
- Verify Modbus communication is stable
- Use **Refresh Data** button for manual update
- Check WiFi module's connection stability
- Review Home Assistant logs for communication errors

### WiFi Module Issues

- **Can't connect to module:** Verify power supply and WiFi connection
- **Communication timeouts:** Check baud rate matches heat pump (usually 9600)
- **Intermittent connection:** Consider assigning static IP or DHCP reservation
- **No data from heat pump:** Verify correct wiring polarity (A+/B-)

## Contributing

Contributions are welcome!

- 🐛 Report bugs via [GitHub Issues](https://github.com/stroeks3/tec_heatpump_modbus/issues)
- 💡 Suggest features via [GitHub Issues](https://github.com/stroeks3/tec_heatpump_modbus/issues)
- 🔧 Submit pull requests with improvements

## Credits

- Based on official TEC Heat Pump documentation
- Inspired by [wjtje/tec-heat-pump](https://github.com/wjtje/tec-heat-pump) repository
- Developed for the Home Assistant community

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation:** GitHub Wiki (coming soon)
- **Issues:** [GitHub Issues](https://github.com/stroeks3/tec_heatpump_modbus/issues)
- **Discussions:** [GitHub Discussions](https://github.com/stroeks3/tec_heatpump_modbus/discussions)

---

⚠️ **Remember:** This is an unofficial community integration. Use at your own risk.
