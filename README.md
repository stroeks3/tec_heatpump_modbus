# TEC Heat Pump Modbus - Home Assistant Integration

![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg) ![GitHub release](https://img.shields.io/github/release/stroeks3/tec_heatpump_modbus.svg) ![License](https://img.shields.io/github/license/stroeks3/tec_heatpump_modbus.svg) ![IoT Class](https://img.shields.io/badge/IoT%20Class-Local%20Polling-blue.svg)

> **Disclaimer:** This is an unofficial integration created by the community, not by TEC (The Energy Combination). TEC does not provide support for it. This is a community project - use it entirely at your own risk. Developed and tested with the TEC RS07VLF 7kW (R32) heat pump.

Home Assistant integration for TEC (The Energy Combination) heat pumps over Modbus TCP. It exposes **86 entities** — every temperature, pressure and alarm the unit reports, plus 30 writable settings — so you can monitor the machine properly and automate around it.

## Features

| Platform | Count | What it covers |
|---|---|---|
| Sensors | **42** | 28 from the unit's registers, 8 status sensors, 6 calculated |
| Numbers | **30** | Writable settings, with min/max limits enforced |
| Binary sensors | **10** | Alarms plus two derived watchdogs, `device_class: problem` |
| Switches | **3** | AC, DHW, SG Function |
| Buttons | **1** | Manual refresh |

Highlights, each described in full under [Available Entities](#available-entities):

- **Refrigerant circuit diagnostics** — suction and discharge superheat plus expansion-valve position, the earliest warning you get for a drifting charge or liquid returning to the compressor
- **Performance sensors** — live thermal power and COP, hourly and daily energy-weighted COP, and the unit's own energy counters
- **Season Mode and DHW Water Limit** — two firmware parameters that were previously only visible on the PGDX panel, and that explain a lot of otherwise puzzling behaviour
- **Compressor diagnostics** — requested versus actual frequency, so you can watch the firmware throttle for pressure or discharge protection

### Configuration

- Setup through the Home Assistant UI, no YAML
- Configurable update interval and timeout
- Multiple heat pumps supported
- Optional custom device naming

### Languages

The **setup dialog** is available in English and Dutch.

**Entity names are English only, deliberately.** Translating them would make entity IDs depend on the installation's locale, which breaks dashboards and automations when they are shared. The English source strings live in `strings.json`; the Dutch translation in `translations/nl.json` covers the config and options flow.

### Robust Modbus communication

- **Persistent TCP connection** — one connection is opened and reused for all polling and writes, instead of reconnecting every update cycle. This is significantly gentler on RTU-to-TCP gateways, most of which allow only a few simultaneous client connections (the HF2211S used here allows 3). Automatic reconnect on connection loss.
- Reads and writes are serialized, so a parameter write never collides with a polling cycle
- Read errors are logged once per function code when they start, not on every poll, so an outage does not flood the log

### Diagnostics

- Standard Home Assistant **Download diagnostics** support (device page → Download diagnostics)
- Includes connection status, coordinator health and a full register dump with current values
- Host/IP details are automatically redacted — safe to attach to GitHub issues

## Prerequisites

- TEC heat pump with Modbus support
- **Modbus RTU to TCP/IP WiFi module (REQUIRED - see setup below)**
- Home Assistant 2025.10.0 or newer
- Network connectivity between Home Assistant and heat pump

## 📡 WiFi Module Setup (Required)

**⚠️ CRITICAL: This integration cannot work without a WiFi module!**

A WiFi module (Modbus RTU to TCP/IP gateway) is essential to enable communication between Home Assistant and your TEC heat pump. The heat pump uses Modbus RTU natively, so you need a converter to bridge to TCP/IP for network connectivity.

### Hardware

**Any transparent Modbus RTU to TCP gateway should work.** The integration talks plain Modbus TCP and does not care which brand sits in between. Pick whatever you can source locally.

**What this integration was built and tested with:**
- **[Hi-Flying HF2211S serial device server (RS485 to WiFi)](https://aliexpress.com/item/1005006115167929.html)**
  - ✅ Easy setup, working within minutes
  - ✅ Reliable performance over months of continuous polling
  - ⚠️ Allows 3 simultaneous TCP clients. Close any other Modbus tool before adding a second one.
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

This is a **custom repository** — it is not in the HACS default store, so it has to be added by URL first.

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

### Sensors (42)

#### From the unit's registers (28)

Water inlet and outlet, ambient, suction and discharge temperature, DHW tank, low and high pressure, water flow, compressor frequency (actual and requested), compressor power, compressor current (motor and AC), pump PWM, fan speed, EEV position, suction and discharge superheat, room temperature, operating hours, operating state, the two unit energy counters, two unidentified counters, plus **Season Mode** and **DHW Water Limit**.

Several of these deserve explanation:

**Suction Superheat / Discharge Superheat** — the earliest warning you get for a refrigerant charge that is drifting, an expansion valve that is not controlling well, or liquid making its way back to the compressor. Both are temperature *differences* in kelvin and carry no `device_class`, so Home Assistant will not mistake them for absolute temperatures and convert 3.5 K to −269.65 °C.

> With the compressor **off** these readings are meaningless, so **both sensors report `unknown` in standby** rather than a misleading number. You do not need to filter on compressor frequency yourself.
>
> Why this matters: read unfiltered, one DHW cycle showed 45% of samples below 2.0 K with a minimum of −5.6 K. The same cycle, counting only samples with the compressor running, gave 6% and +0.2 K. A factor seven, in the alarming direction.

**EEV Position** — the electronic expansion valve's step position. Read it next to the superheat figures: a valve pinned at an end stop has run out of room to regulate, which the superheat alone would not tell you.

**Season Mode** — whether the unit is set to `Heating` or `Cooling`. This is the firmware's own mode flag (HR 1), set on the PGDX panel and until now only visible there. Read-only over Modbus.

> It is called Season Mode, not Operating Mode, on purpose: it reads `Cooling` all summer regardless of what the unit is doing at that moment. For the current activity use **Operating State**.

**DHW Water Limit** — ST21, the absolute water temperature the unit holds itself to while heating hot water. This is what actually ends a DHW cycle: once the tank is warm enough that reaching it would need water hotter than this, the compressor stops and retries after its minimum-off time. If your hot-water cycles keep restarting a few minutes apart without reaching setpoint, compare this figure with **Water Outlet** — they will be equal at every stop.

**Unit Thermal Energy Total / Unit Electrical Energy Total** — the heat pump's own cumulative energy counters, so COP no longer has to be reconstructed from a power register with 0.1 kW resolution. Confirmed against independently integrated energy over a 77-minute DHW cycle: 3.73 against 3.59. Two caveats: they update roughly every 20 minutes of compressor runtime rather than continuously, so do not read them over a short window; and being 16-bit at 0.1 kWh they wrap every 6553.5 kWh, which makes the absolute readings useless as lifetime totals but leaves them perfectly good as an incremental source.

**Compressor Frequency Requested** — the PID's requested speed alongside the actual one. When the firmware throttles for pressure or discharge protection, the two diverge and you can see it happen.

**Compressor Current (Motor / AC)** — finer-grained than the power register (0.1 A ≈ 23 W against 0.1 kW), so they show load changes that the power reading rounds away.

**Fan Speed** — the EC fan's drive voltage. It reads 0 whenever the fan is off, and during operation it runs between CN02 (minimum fan speed) and CN01 (maximum), so it shows you the fan modulating with load.

> Released in 2026.08.04 as *Pump Speed Feedback*, which was wrong. IR 15 tracks the compressor, not the pump: it stays 0 while the pump ramps up, rises seconds before the compressor starts, and returns to 0 the instant the compressor stops, a full minute before the pump does. See [Upgrading to 2026.08.05](#upgrading-to-20260805).

**Unit Counter IR16 / IR27** — exposed for investigation, not for use. IR 16 held a constant value through an hour and a half of full load, so it is not a counter — more likely a fixed code. IR 27 runs a sawtooth from 0 to roughly 34–41 and back over 4–7 minutes, but only during the last 20 minutes of a DHW cycle when discharge superheat is high, and the superheat drops on every reset. It reads as a periodic valve or oil-return action. If you recognise either, please open an issue.

#### Status sensors from discrete inputs (8)

Primary pump, secondary pump, AC heater, crankcase heater, DHW circulation pump, DHW electric heater, gas boiler, and **AC Enable Status** — the unit's own confirmation that the AC master enable landed, useful if you drive that switch from an automation.

#### Calculated performance sensors (6)

- **Thermal Power (kW)** — live heat delivered to the water, calculated from water flow × temperature difference (positive = heating, negative = cooling)
- **COP** — live coefficient of performance (thermal power ÷ compressor electrical power). Only shown while the compressor draws at least 0.5 kW: the power register has 0.1 kW resolution, so below that the reading would be dominated by rounding noise. `Unknown` otherwise, so your statistics stay clean.
- **COP (1h Average)** — energy-weighted COP over the past hour (total heat ÷ total electrical energy). The averaging cancels out register rounding noise, so this one is also meaningful during low-load operation, such as summer cooling at minimum compressor speed. Shown once at least 0.05 kWh was consumed within the hour; resets on restart.
- **COP (Today)** — energy-weighted COP since local midnight, built on persistent energy counters, so it survives restarts.
- **Thermal Energy / Compressor Energy (kWh)** — cumulative counters, persisted across restarts. Thermal counts |heat| moved to or from the water, so heating and cooling both add. Usable in the Home Assistant Energy dashboard.

> Electrical power is the compressor inverter reading. The backup electric heater sits on a separate circuit and is **not** included in any COP figure.

### Number Entities (30) — Writable Settings

Adjustable directly from the Home Assistant UI or via `number.set_value`. Limits follow the manual, tightened where a wider range makes no physical sense (a pump *minimum* speed of 100% for instance), and following the unit where the manual contradicts itself: CM17 and CM18 both list a factory default outside their own stated min/max, and this unit shipped with CM17 at 95 against a stated maximum of 80.

- Temperature setpoints (cooling, heating, DHW) and hysteresis
- Heating/cooling curve compensation factors
- Compressor frequency limits (heating & DHW: rated/min/max)
- Indoor pump parameters (target dT, min/max speed, min flow alarm)
- DHW circulation pump timings
- Room temperature setting

**Register IDs:** `st01`, `st02`, `st03`, `st04`, `st06`, `st07`, `st08`, `st09`, `st10`, `st11`, `st12`, `st13`, `st14`, `st15`, `st16`, `st17`, `st18`, `st33`, `st34`, `room_temperature_setting`, `cm14`, `cm15`, `cm16`, `cm17`, `cm18`, `ev03`, `ev04`, `ev05`, `ev06`, `ev07`

### Alarm Binary Sensors (10)

Real `binary_sensor` entities with `device_class: problem` — they show up red in the UI and work directly with notification automations and blueprints:

- Low/high pressure alarm, low/high outlet temperature alarm, low flow alarm
- LP/HP alarm count exceeded (24h protection counters)
- **Inverter Alarm** (latched IGBT failure bit — observed and verified live on an RS07V/LF during a real inverter trip)

The outlet-temperature alarms carry a two-minute delay: they briefly trip when the three-way valve switches back from the DHW circuit and the sensor still sees hot tank water. That transient is not a fault, so it no longer raises an alarm — a genuine fault persists and still comes through.

**Pump Flow Fault** is the one derived entity here: the pump is being commanded but no water is moving. It turns on when pump PWM is above zero while water flow stays under 0.3 m³/h for a full minute.

Why it exists, when the unit already has its own low-flow alarm: below roughly 23% PWM the pump can stop moving water while the controller still believes it is running. With the compressor on, no circulation means nothing carrying heat away from the inverter, which is the documented contributor to one RS07V/LF's IGBT trip. The unit's AL17 uses its own threshold (EV07 × 0.8 for 5 seconds) and clears the moment flow creeps back over the line, so a pump that is barely moving water never latches anything.

The 0.3 m³/h threshold sits well under the 0.6–0.7 measured at the 23% floor and well over the 0.0 seen with the pump off, so it separates "barely turning" from "not moving water at all". The one-minute hold covers the ramp after the pump starts.

**Low Suction Superheat** turns on when suction superheat stays under 2.0 K for two minutes while the compressor runs. Superheat near zero means refrigerant is leaving the evaporator without fully evaporating, so liquid reaches the compressor, dilutes the oil, and in the extreme causes slugging.

Brief dips are ordinary valve regulation and stay quiet. The threshold pair is empirical and the obvious settings do not work: 3 minutes under 1.5 K never fired at all, despite a 273-second dip to −0.2 K in the same cycle, because the reading oscillates and keeps bouncing briefly back over 1.5 K. At 2 minutes under 2.0 K that dip fires and an 81-second one does not.

No compressor condition is needed in your automations: the superheat sensor itself reports `unknown` when the compressor is stopped, and `unknown` is never below the threshold.

### Switches (3)

- AC Switch (DI4)
- DHW Switch (DI5)
- SG Function (TR12)

### Buttons (1)

- Refresh Data

## Writing Values

**Recommended:** use the number entities directly, e.g. in an automation:

```yaml
action: number.set_value
target:
  entity_id: number.tec_heat_pump_cooling_setpoint
data:
  value: 21.3
```

Values are shown and set in display units; the integration converts to raw register values automatically (21.3 °C ↔ raw 213 with scale 0.1).

**Deprecated (still works):** the `tec_heatpump_modbus.write_register` service:

```yaml
action: tec_heatpump_modbus.write_register
data:
  sensor: st01  # Register unique ID
  value: 21.3   # Value (automatically scaled)
```

### Failed writes are loud

Since **2026.08.04**, a write that does not land raises an error instead of only logging one:

- Switching AC, DHW or SG on or off raises `HomeAssistantError` if the Modbus write fails, so the automation stops and you get a trace. Previously a failed write was indistinguishable from a successful one.
- `write_register` raises a validation error when the register name does not exist or is not writable, instead of silently doing nothing.

If an automation of yours starts going red after upgrading, it was already failing — it just was not telling you.

## Versioning

Releases use **CalVer**: `yyyy.MM.NN`, where `NN` counts releases within that month (`2026.08.01`, `2026.08.02`, …). Pre-releases add `-beta.N` and are published as GitHub pre-releases, so HACS only offers them if you opt into betas.

Versions up to and including `v2.3.0-beta.1` used semantic versioning. `2026.08.01` was the first CalVer release; the scheme will not change back, because going from `2026.08.x` to `3.0.0` would read as a downgrade to HACS.

### ⚠️ Upgrading to 2026.08.05

**`Pump Speed Feedback` is renamed to `Fan Speed`** (breaking, but it only existed in 2026.08.04, for one day).

IR 15 was published as the circulation pump's speed feedback. It is not: it is the EC fan's drive voltage. Watching a full cycle rather than only standby made that plain. The pump ramped from 23% to 90% while the register stayed at 0; it rose to 280 seven seconds *before* the compressor started, and dropped back to 0 the instant the compressor stopped, a full minute before the pump did. The value range settles it: 280–325 against CN02 (minimum fan speed) of exactly 2.80 V and CN01 (maximum) of 3.70 V. So it is volts at scale 0.01, and it is the fan.

- The old entity is orphaned. Delete `sensor.<device>_pump_speed_feedback` from the entity registry; the new `sensor.<device>_fan_speed` appears alongside it.
- History under the old entity is not migrated, and would have been mislabelled anyway.
- The README claim that it "works as a running indicator" for a stalled pump was wrong in the worst direction: in standby the pump genuinely circulates (0.6–0.7 m³/h) while IR 15 reads 0. Anything built on it would have fired constantly.

**New: `binary_sensor.<device>_pump_flow_fault`**, which does what IR 15 was wrongly credited with, using water flow against commanded pump PWM. See [Alarm Binary Sensors](#alarm-binary-sensors-9).

### ⚠️ Upgrading from 1.x to 2.0

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

> **Note for contributors:** register reads span the lowest to the highest address in a single batch, so one outlying address widens the whole block. Modbus FC03/FC04 allow at most 125 registers per read, and the holding-register block currently spans 1..121. Any new holding register above address 125 needs chunking first, the way the bit reads already do.

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

When attaching diagnostics to an issue, use the device page's **Download diagnostics** button — host and IP details are redacted automatically.

## Credits

- Based on official TEC Heat Pump documentation
- Inspired by [wjtje/tec-heat-pump](https://github.com/wjtje/tec-heat-pump) repository
- Developed for the Home Assistant community

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

Questions, bug reports and feature requests all go through [GitHub Issues](https://github.com/stroeks3/tec_heatpump_modbus/issues).

---

⚠️ **Remember:** This is an unofficial community integration. Use at your own risk.
