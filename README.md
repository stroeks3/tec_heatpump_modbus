# TEC Heat Pump Modbus - Home Assistant Integration

![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg) ![GitHub release](https://img.shields.io/github/release/stroeks3/tec_heatpump_modbus.svg) ![License](https://img.shields.io/github/license/stroeks3/tec_heatpump_modbus.svg) ![IoT Class](https://img.shields.io/badge/IoT%20Class-Local%20Polling-blue.svg)

> **Disclaimer:** This is an unofficial integration created by the community, not by TEC (The Energy Combination). TEC does not provide support for it. This is a community project - use it entirely at your own risk. Developed and tested with the TEC RS07VLF 7kW (R32) heat pump.

A comprehensive Home Assistant integration for TEC (The Energy Combination) heat pumps using Modbus TCP protocol. Monitor and control your heat pump with 50+ entities for complete visibility and automation.

## Features

### 📊 Comprehensive Monitoring & Control (60+ entities)

- **30 Number Entities** - Writable settings (setpoints, compressor frequency limits, pump parameters) adjustable directly from the UI, with documented min/max limits enforced
- **25 Read-Only Sensors** - Temperatures, pressures, flow, power, currents, superheat, operating hours
- **14 Discrete Inputs** - Alarms and status indicators for all major components
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

### 🔧 Writing Values

Control your heat pump by adjusting writable registers:

- **Number entities** (recommended) - set values directly in the UI or via `number.set_value`; min/max limits are enforced
- `tec_heatpump_modbus.write_register` service - deprecated, kept for backwards compatibility
- Automatic value scaling and conversion (e.g. 21.3°C ↔ raw register value 213)

### 📈 Calculated Performance Sensors

- **Thermal Power (kW)** — live heat delivered to the water, calculated from
  water flow × temperature difference (positive = heating, negative = cooling)
- **COP** — live coefficient of performance (thermal power ÷ compressor
  electrical power). Only shown while the compressor draws at least 0.5 kW:
  the power register has 0.1 kW resolution, so below that the reading would
  be dominated by rounding noise. "Unknown" otherwise, so your statistics
  stay clean.
- **COP (1h Average)** — energy-weighted COP over the past hour (total heat ÷
  total electrical energy). The averaging cancels out register rounding
  noise, so this one is also meaningful during low-load operation (e.g.
  summer cooling at minimum compressor speed). Shown once at least 0.05 kWh
  was consumed within the hour; resets on restart.
- **COP (Today)** — energy-weighted COP since local midnight, built on
  persistent energy counters (survives restarts).
- **Thermal Energy / Compressor Energy (kWh)** — cumulative counters,
  persisted across restarts. Thermal counts |heat| moved to or from the
  water (heating and cooling both add). Usable in the HA Energy dashboard.
- Note: electrical power is the compressor inverter reading — the backup
  E-heater (separate circuit) is not included in any COP.

### ⚡ Compressor Diagnostics

- **Compressor Current (Motor / AC)** — the current readings the unit reports.
  Finer-grained than the power register (0.1 A ≈ 23 W against 0.1 kW), so they
  show load changes that the power reading rounds away.
- **Compressor Frequency Requested** — the PID's requested speed alongside the
  actual one. When the firmware throttles for pressure or discharge protection,
  the two diverge and you can see it happen.

### 🧊 Refrigerant Circuit Diagnostics

- **Suction Superheat** and **Discharge Superheat** — the earliest warning you
  get for a refrigerant charge that is drifting, an expansion valve that is not
  controlling well, or liquid making its way back to the compressor. Both are
  temperature *differences* in kelvin and carry no `device_class`, so Home
  Assistant will not mistake them for absolute temperatures.
- **EEV Position** — the electronic expansion valve's step position. Read it
  next to the superheat figures: a valve pinned at an end stop has run out of
  room to regulate, which the superheat alone would not tell you.
- **Operating Mode** — whether the unit is in `Heating` or `Cooling`. This is
  the firmware's own mode flag (HR 1), set on the PGDX panel and until now only
  visible there. Read-only over Modbus.
- **Pump Speed Feedback** — the circulation pump's own speed reading, published
  raw. It reads 0 whenever the pump is off, so it works as a running indicator;
  a commanded speed with no feedback is what a stalled pump looks like, and the
  controller does not flag that by itself. The unit is unresolved: it read 280
  against a commanded 90.0%, so it is not a percentage of the command.

### 🔢 Energy Totals From the Unit

- **Unit Thermal Energy Total** and **Unit Electrical Energy Total** — the heat
  pump's own cumulative energy counters, so COP no longer has to be reconstructed
  from a power register with 0.1 kW resolution. Confirmed against independently
  integrated energy over a 77-minute DHW cycle: 3.73 against 3.59.
- They update roughly every 20 minutes of compressor runtime rather than
  continuously, so do not read them over a short window. Being 16-bit at 0.1 kWh
  they also wrap every 6553.5 kWh, which makes the absolute readings useless as
  lifetime totals but leaves them perfectly good as an incremental source.
- **AC Enable Status** — the unit's own confirmation that the AC master enable
  landed, useful if you drive that switch from an automation.

### 🔌 Robust Modbus Communication

- **Persistent TCP connection** — one connection is opened and reused for all polling and writes, instead of reconnecting every update cycle. This is significantly gentler on RTU-to-TCP gateways, most of which allow only a few simultaneous client connections (the popular USR-W610 allows 3). Automatic reconnect on connection loss.
- Reads and writes are serialized, so a parameter write never collides with a polling cycle

### 🩺 Diagnostics

- Standard Home Assistant **Download diagnostics** support (device page → Download diagnostics)
- Includes connection status, coordinator health and a full register dump with current values
- Host/IP details are automatically redacted — safe to attach to GitHub issues

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

## Removal

1. Go to **Settings → Devices & Services → TEC Heat Pump Modbus**, open the integration and choose **Delete** (three dots menu) for each configured heat pump. This removes the config entry, its device and all entities, and stops the Modbus polling.
2. If you no longer want the integration available at all:
   - **HACS install:** open HACS → Integrations → TEC Heat Pump Modbus → three dots (⋮) → **Remove**.
   - **Manual install:** delete the `custom_components/tec_heatpump_modbus` folder from your Home Assistant config directory.
3. Restart Home Assistant to complete the removal.

Removing the integration also deletes its persisted per-device energy counters (used for the Thermal/Compressor Energy sensors and daily COP); these cannot be recovered afterwards.

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

### Number Entities (30) — Writable Settings

Adjustable directly from the Home Assistant UI (with documented min/max limits enforced) or via `number.set_value`:

- Temperature setpoints (cooling, heating, DHW) and hysteresis
- Heating/cooling curve compensation factors
- Compressor frequency limits (heating & DHW: rated/min/max)
- Indoor pump parameters (target dT, min/max speed, min flow alarm)
- DHW circulation pump timings
- Room temperature setting

**Register IDs:** `st01`, `st02`, `st03`, `st04`, `st06`, `st07`, `st08`, `st09`, `st10`, `st11`, `st12`, `st13`, `st14`, `st15`, `st16`, `st17`, `st18`, `st33`, `st34`, `room_temperature_setting`, `cm14`, `cm15`, `cm16`, `cm17`, `cm18`, `ev03`, `ev04`, `ev05`, `ev06`, `ev07`

### Sensors (25) — Read-Only

- Water inlet/outlet temperatures
- Outdoor ambient temperature
- Suction/discharge temperatures
- DHW tank temperature
- Low/high pressure side
- Water flow
- Compressor frequency & operating hours
- Compressor power consumption and motor/AC currents
- Suction and discharge superheat, EEV step position
- Pump PWM commanded and pump speed feedback
- Unit operating state and heating/cooling mode

### Alarm Binary Sensors (8)

Real `binary_sensor` entities with `device_class: problem` — they show up red in
the UI when active and work directly with notification automations and blueprints:

- Low/high pressure alarm, low/high outlet temperature alarm, low flow alarm
- LP/HP alarm count exceeded (24h protection counters)
- **Inverter Alarm** (latched IGBT failure bit — observed and verified live on an
  RS07V/LF during a real inverter trip)

The outlet-temperature alarms carry a two-minute delay: they briefly trip when
the three-way valve switches back from the DHW circuit and the sensor still
sees hot tank water. That transient is not a fault, so it no longer raises an
alarm — a genuine fault persists and still comes through.

### Status Sensors — Discrete Inputs (7)

- Primary/secondary pump, heaters, DHW circulation pump, gas boiler

### Switches (3)

- AC Switch (DI4)
- DHW Switch (DI5)
- SG Function (TR12)

### Buttons (1)

- Refresh Data

## Writing Values

**Recommended:** use the number entities directly, e.g. in an automation:

```yaml
service: number.set_value
target:
  entity_id: number.tec_heat_pump_cooling_setpoint
data:
  value: 21.3
```

Values are shown and set in display units; the integration converts to raw register values automatically (21.3°C ↔ raw 213 with scale 0.1).

**Deprecated (still works):** the `tec_heatpump_modbus.write_register` service:

```yaml
service: tec_heatpump_modbus.write_register
data:
  sensor: st01  # Register unique ID
  value: 21.3   # Value (automatically scaled)
```

## ⚠️ Upgrading from 1.x to 2.0

Writable settings moved from `sensor.*` to `number.*` entities (**breaking change**):

- `sensor.tec_heat_pump_cooling_setpoint` → `number.tec_heat_pump_cooling_setpoint` (same pattern for all 30 writable registers)
- Update dashboards and automations that reference the old `sensor.*` entity IDs
- The `write_register` service keeps working unchanged
- Long-term statistics recorded under the old sensor entities are not migrated

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
