"""The TEC Heat Pump Modbus integration."""
from __future__ import annotations
import asyncio
import logging
import time
from datetime import timedelta
from collections import defaultdict, deque
from typing import Any
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from .const import (
    CONF_NAME,
    CONF_DEVICE_ID,
    CONF_DELAY,
    CONF_TIMEOUT,
    DEFAULT_NAME,
    DEFAULT_DELAY,
    DOMAIN,
    BINARY_SENSORS,
    NUMBERS,
    SENSORS,
    SWITCHES,
    REGISTER_TYPE_COIL,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.BUTTON,
    Platform.SWITCH,
]

# Bit-based Modbus functions (coils / discrete inputs) are read in chunks:
# some RTU-to-TCP gateways and devices are unreliable with large bit reads.
MAX_BITS_PER_READ = 32

# Modbus function codes read on the slow cadence instead of every poll.
# Function 3 is the holding-register block: writable parameters plus two
# read-only settings, all of which only change when something writes them.
SLOW_FUNCTIONS = frozenset({3})
SLOW_READ_INTERVAL_S = 60.0


type TECHeatPumpConfigEntry = ConfigEntry[TECHeatPumpCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: TECHeatPumpConfigEntry) -> bool:
    """Set up from a config entry."""
    coordinator = TECHeatPumpCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def write_register_service(call: ServiceCall):
        """Service handler to write a value to a register.

        Kept for backwards compatibility with existing automations;
        writable registers are also exposed as number entities.
        """
        sensor_name = call.data.get("sensor")
        value_to_write = call.data.get("value")
        sensor_config = next(
            (s for s in NUMBERS if s.get("unique_id") == sensor_name and s.get("writable")),
            None,
        )
        if not sensor_config:
            raise ServiceValidationError(
                f"Register '{sensor_name}' is not found or not writable."
            )
        # Convert scaled value back to raw register value (e.g., 21.3°C -> 213).
        # round() instead of int(): int(21.3 / 0.1) truncates to 212.
        raw_value = round(value_to_write / sensor_config.get("scale", 1.0))
        # Two's complement for signed registers (e.g. -10.0°C -> 65436)
        if raw_value < 0:
            raw_value += 65536
        device_id = coordinator.device_id
        address = sensor_config["address"]
        _LOGGER.info(
            "Service 'write_register' called for %s. Writing raw value %s to address %s on device %s",
            sensor_name,
            raw_value,
            address,
            device_id,
        )
        await coordinator.api_write_register(
            address=address, value=raw_value, device_id=device_id
        )
        await coordinator.async_request_refresh()

    write_register_schema = vol.Schema(
        {
            vol.Required("sensor"): cv.string,
            vol.Required("value"): vol.Coerce(float),
        }
    )
    hass.services.async_register(
        DOMAIN, "write_register", write_register_service, schema=write_register_schema
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TECHeatPumpConfigEntry) -> bool:
    """Unload a config entry."""
    hass.services.async_remove(DOMAIN, "write_register")
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_close()
    return unload_ok


class TECHeatPumpCoordinator(DataUpdateCoordinator):
    """Data coordinator for the TEC Heat Pump.

    Maintains a single persistent Modbus TCP connection that is shared by
    the polling loop and all writes (serialized by a lock). This avoids a
    connect/disconnect cycle every poll, which matters on RTU-to-TCP
    gateways with a limited number of simultaneous client slots.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.host = entry.data[CONF_HOST]
        self.port = entry.data[CONF_PORT]
        self.device_id = entry.data[CONF_DEVICE_ID]
        self.timeout = entry.data[CONF_TIMEOUT]
        self.entry = entry
        self._client = None
        self._modbus_lock = asyncio.Lock()
        # Rolling window of (monotonic time, |thermal kW|, electrical kW)
        # samples for the 1h-average COP
        self._cop_samples: deque = deque()
        # Persistent energy counters (kJ) for the energy sensors and the
        # daily COP; survive restarts via HA storage.
        self._store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.energy")
        self._energy = {
            "thermal_kj": 0.0,
            "elec_kj": 0.0,
            "day": None,
            "day_start_thermal_kj": 0.0,
            "day_start_elec_kj": 0.0,
        }
        self._last_poll_t = None
        self._last_store_save = 0.0
        # Function codes currently failing to read; used to log a Modbus
        # read error only once per outage instead of on every poll.
        self._logged_read_errors: set[int] = set()
        # Holding registers are configuration, not measurements: they change
        # only when something writes them. Re-reading all 121 of them every
        # few seconds is almost pure waste on a 9600-baud RS485 line, where
        # that one read costs roughly 310 ms against 80 ms for the whole
        # input-register block. So they are polled on a slow cadence, their
        # values cached between reads, and refreshed immediately after any
        # write so the UI never shows a stale setpoint.
        self._slow_cache: dict[str, Any] = {}
        self._slow_last_read: float | None = None
        self._slow_read_due = True
        device_name = entry.data.get(CONF_NAME, entry.title or DEFAULT_NAME)
        delay = entry.data.get(CONF_DELAY, DEFAULT_DELAY)
        update_interval = timedelta(seconds=delay)
        # config_entry is required since HA 2026.8 (hard error when omitted)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            config_entry=entry,
        )
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=device_name,
            manufacturer="TEC",
            model="Heat Pump",
        )

    @property
    def client_connected(self) -> bool:
        """Return True if the persistent Modbus connection is open."""
        return self._client is not None and self._client.is_socket_open()

    async def _async_get_client(self):
        """Return a connected Modbus client, (re)connecting if needed.

        Must be called while holding self._modbus_lock.
        """
        from pymodbus.client import ModbusTcpClient

        if self._client is None:
            self._client = ModbusTcpClient(
                host=self.host, port=self.port, timeout=self.timeout
            )
        if not self._client.is_socket_open():
            if not await self.hass.async_add_executor_job(self._client.connect):
                raise UpdateFailed(f"Failed to connect to {self.host}:{self.port}")
            _LOGGER.debug("Modbus connection (re)established to %s:%s", self.host, self.port)
        return self._client

    async def _async_drop_client(self) -> None:
        """Close the connection so the next call starts with a clean socket.

        Must be called while holding self._modbus_lock.
        """
        if self._client is None:
            return
        try:
            await self.hass.async_add_executor_job(self._client.close)
        except Exception:  # noqa: BLE001 - best effort cleanup
            pass

    async def _async_setup(self) -> None:
        """Load the persisted energy counters before the first refresh."""
        stored = await self._store.async_load()
        if stored:
            self._energy.update(stored)

    async def async_close(self) -> None:
        """Close the Modbus connection (called on unload)."""
        await self._store.async_save(dict(self._energy))
        async with self._modbus_lock:
            await self._async_drop_client()
            self._client = None

    async def _async_update_data(self) -> dict:
        """Fetch data from API endpoint."""
        all_entities = SENSORS + BINARY_SENSORS + NUMBERS + SWITCHES
        data = {}

        async with self._modbus_lock:
            client = await self._async_get_client()
            try:
                # Group entities by device_id and function code for efficient batch reading
                entity_groups = defaultdict(list)
                for entity_config in all_entities:
                    function_code = entity_config.get("function")
                    # Fallback for switches: use function 2 (read discrete inputs) for coils
                    if not function_code and entity_config.get("register_type") == REGISTER_TYPE_COIL:
                        function_code = 2
                    if not function_code:
                        continue
                    key = (self.device_id, function_code)
                    entity_groups[key].append(entity_config)

                # Decide once per poll whether the slow group is due, so every
                # slow function code in this cycle is treated consistently.
                now_m = time.monotonic()
                slow_due = (
                    self._slow_read_due
                    or self._slow_last_read is None
                    or (now_m - self._slow_last_read) >= SLOW_READ_INTERVAL_S
                )
                slow_read_ok = True

                for (device_id, function_code), entities in entity_groups.items():
                    if function_code in SLOW_FUNCTIONS and not slow_due:
                        # Serve from the previous read. Missing keys stay absent
                        # rather than being written as None, so a genuine read
                        # failure still surfaces as unknown.
                        for entity in entities:
                            uid = entity["unique_id"]
                            if uid in self._slow_cache:
                                data[uid] = self._slow_cache[uid]
                        continue

                    modbus_func_map = {
                        1: client.read_coils,
                        2: client.read_discrete_inputs,
                        3: client.read_holding_registers,
                        4: client.read_input_registers,
                    }
                    read_func = modbus_func_map.get(function_code)
                    if not read_func:
                        continue

                    min_addr = min(s["address"] for s in entities)
                    max_addr = max(s["address"] for s in entities)

                    if function_code in (1, 2):
                        # Bit reads: chunked, sparse addresses allowed
                        bits_by_addr = {}
                        addr = min_addr
                        while addr <= max_addr:
                            chunk = min(MAX_BITS_PER_READ, max_addr - addr + 1)
                            result = await self.hass.async_add_executor_job(
                                lambda a=addr, c=chunk: read_func(address=a, count=c, device_id=device_id)
                            )
                            if result.isError():
                                if function_code not in self._logged_read_errors:
                                    self._logged_read_errors.add(function_code)
                                    _LOGGER.warning(
                                        f"Modbus error reading function {function_code} at {addr}: {result}"
                                    )
                            else:
                                self._logged_read_errors.discard(function_code)
                                for i in range(chunk):
                                    bits_by_addr[addr + i] = result.bits[i]
                            addr += chunk
                        for entity in entities:
                            data[entity["unique_id"]] = bits_by_addr.get(entity["address"])
                        continue

                    # Register reads: all addresses in one batch for efficiency.
                    # NOTE: this spans min..max, so a single low or high address widens
                    # the whole block. Modbus FC03/FC04 allow at most 125 registers per
                    # read. Adding HR 1 (mode) in 2026.08.04 took the holding-register
                    # block to 1..121 = 121 registers, leaving only 4 spare. Any new
                    # holding register above 125 needs chunking first, the way the bit
                    # reads above already do.
                    count = max_addr - min_addr + 1
                    result = await self.hass.async_add_executor_job(
                        lambda: read_func(address=min_addr, count=count, device_id=device_id)
                    )

                    if result.isError():
                        if function_code not in self._logged_read_errors:
                            self._logged_read_errors.add(function_code)
                            _LOGGER.warning(f"Modbus error reading function {function_code}: {result}")
                        if function_code in SLOW_FUNCTIONS:
                            # Do not restart the slow timer on a failed read, and
                            # keep serving the last good values in the meantime.
                            slow_read_ok = False
                            for entity in entities:
                                uid = entity["unique_id"]
                                if uid in self._slow_cache:
                                    data[uid] = self._slow_cache[uid]
                        continue
                    self._logged_read_errors.discard(function_code)

                    for entity in entities:
                        offset = entity["address"] - min_addr
                        value = None
                        if hasattr(result, "registers") and len(result.registers) > offset:
                            raw_value = result.registers[offset]
                            # Convert unsigned to signed int16 if needed
                            value = (
                                raw_value - 65536
                                if entity.get("data_type") == "int16" and raw_value > 32767
                                else raw_value
                            )
                            # Apply scaling factor (e.g., 0.1 to convert 250 to 25.0°C)
                            if "scale" in entity:
                                value *= entity["scale"]
                        data[entity["unique_id"]] = value
                        if function_code in SLOW_FUNCTIONS:
                            self._slow_cache[entity["unique_id"]] = value

                if slow_due and slow_read_ok:
                    self._slow_last_read = now_m
                    self._slow_read_due = False

            except UpdateFailed:
                await self._async_drop_client()
                raise
            except Exception as e:
                # Drop the socket so the next poll reconnects cleanly
                await self._async_drop_client()
                raise UpdateFailed(f"Error communicating with device: {e}")

        self._add_calculated_values(data)
        return data

    def _add_calculated_values(self, data: dict) -> None:
        """Derive thermal power, live COP and 1h-average COP.

        Thermal power (kW) = flow (m³/h) x dT (K) x 1.163 kWh/(m³·K).
        Positive while heating the water, negative while cooling.

        Live COP = |thermal| / electrical, only while the compressor draws
        at least 0.5 kW: the power register has 0.1 kW resolution, so below
        ~0.5 kW the quantization error dominates the ratio. Otherwise None,
        so HA shows "unknown" instead of a bogus number.

        1h-average COP is energy-weighted over the past hour
        (sum of heat / sum of electrical energy), which averages the
        quantization noise away and therefore also works at low loads.
        Shown once at least 0.05 kWh was consumed within the window.
        """
        inlet = data.get("b1")
        outlet = data.get("b2")
        flow = data.get("flow")
        elec = data.get("compressor_power")
        freq = data.get("compressor")

        thermal = None
        if None not in (inlet, outlet, flow):
            thermal = round(flow * (outlet - inlet) * 1.163, 2)
        data["thermal_power"] = thermal

        cop = None
        if thermal is not None and freq and elec is not None and elec >= 0.5:
            ratio = abs(thermal) / elec
            # Guard against sensor glitches (COP outside 0..15 is not real)
            if 0 < ratio <= 15:
                cop = round(ratio, 2)
        data["cop"] = cop

        # --- 1h energy-weighted average COP ---
        now = time.monotonic()
        # Samples count while the compressor RUNS (freq > 0). Selecting by
        # state instead of by measured power avoids selection bias: at very
        # low loads the 0.1 kW power register rounds down half the time, and
        # dropping exactly those samples would systematically under-count
        # the electrical energy (inflating the COP). Standby (freq = 0)
        # still contributes nothing.
        if thermal is not None and elec is not None and freq:
            self._cop_samples.append((now, abs(thermal), elec))
        cutoff = now - 3600
        while self._cop_samples and self._cop_samples[0][0] < cutoff:
            self._cop_samples.popleft()

        heat_kj = 0.0
        energy_kj = 0.0
        prev_t = None
        for t, th, el in self._cop_samples:
            if prev_t is not None:
                # Cap the gap so pauses between runs don't fabricate energy
                dt = min(t - prev_t, 30.0)
                heat_kj += th * dt
                energy_kj += el * dt
            prev_t = t

        cop_1h = None
        # 0.05 kWh = 180 kJ minimum consumed energy in the window
        if energy_kj >= 180.0:
            ratio = heat_kj / energy_kj
            if 0 < ratio <= 15:
                cop_1h = round(ratio, 2)
        data["cop_1h"] = cop_1h

        # --- Persistent energy counters + daily COP ---
        e = self._energy
        today = dt_util.now().date().isoformat()
        if e["day"] != today:
            # Local midnight rollover: snapshot the counters as the
            # baseline for today's COP
            e["day"] = today
            e["day_start_thermal_kj"] = e["thermal_kj"]
            e["day_start_elec_kj"] = e["elec_kj"]

        dt_s = 0.0
        if self._last_poll_t is not None:
            # Cap the gap so restarts/hiccups don't fabricate energy
            dt_s = min(now - self._last_poll_t, 30.0)
        self._last_poll_t = now
        # Same state-based criterion as the 1h window (see above)
        if dt_s > 0 and thermal is not None and elec is not None and freq:
            e["thermal_kj"] += abs(thermal) * dt_s
            e["elec_kj"] += elec * dt_s

        data["thermal_energy"] = round(e["thermal_kj"] / 3600.0, 2)
        data["compressor_energy"] = round(e["elec_kj"] / 3600.0, 2)

        cop_daily = None
        day_thermal = e["thermal_kj"] - e["day_start_thermal_kj"]
        day_elec = e["elec_kj"] - e["day_start_elec_kj"]
        # 0.1 kWh = 360 kJ minimum consumed energy today
        if day_elec >= 360.0:
            ratio = day_thermal / day_elec
            if 0 < ratio <= 15:
                cop_daily = round(ratio, 2)
        data["cop_daily"] = cop_daily

        # Persist periodically so the counters also survive a crash or
        # power loss (a plain debounce would be postponed by every poll
        # and only ever flush on clean shutdown).
        if now - self._last_store_save >= 300:
            self._last_store_save = now
            self._store.async_delay_save(lambda: dict(self._energy), 1)

    def force_slow_read(self) -> None:
        """Make the next poll re-read the slow (holding-register) group.

        Called after any write and by the Refresh Data button, so a changed
        setpoint shows up at once instead of on the next slow cadence.
        """
        self._slow_read_due = True

    async def api_write_register(self, address: int, value: int, device_id: int) -> None:
        """Write a single holding register."""
        async with self._modbus_lock:
            client = await self._async_get_client()
            try:
                result = await self.hass.async_add_executor_job(
                    lambda: client.write_register(address=address, value=value, device_id=device_id)
                )
            except Exception as e:
                await self._async_drop_client()
                raise UpdateFailed(f"Error writing register {address}: {e}")
            if result.isError():
                _LOGGER.error("Failed to write register %s: %s", address, result)
                raise UpdateFailed("Failed to write register")
        # Holding registers are on the slow cadence, so without this the UI
        # would keep showing the old setpoint for up to a minute after a write.
        self.force_slow_read()

    async def write_coil(self, address: int, value: bool, device_id: int) -> None:
        """Write a single coil."""
        async with self._modbus_lock:
            client = await self._async_get_client()
            try:
                result = await self.hass.async_add_executor_job(
                    lambda: client.write_coil(address=address, value=value, device_id=device_id)
                )
            except Exception as e:
                await self._async_drop_client()
                raise UpdateFailed(f"Error writing coil {address}: {e}")
            if result.isError():
                _LOGGER.error(f"Failed to write coil {address}: {result}")
                raise UpdateFailed("Failed to write coil")
