"""The TEC Heat Pump Modbus integration."""
from __future__ import annotations
import logging
from datetime import timedelta
from collections import defaultdict
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity import DeviceInfo
from .const import (
    CONF_NAME,
    CONF_DEVICE_ID,
    CONF_DELAY,
    CONF_TIMEOUT,
    DEFAULT_NAME,
    DEFAULT_DELAY,
    DOMAIN,
    SENSORS,
    SWITCHES,
    REGISTER_TYPE_COIL,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    coordinator = TECHeatPumpCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def write_register_service(call: ServiceCall):
        """Service handler to write a value to a register."""
        sensor_name = call.data.get("sensor")
        value_to_write = call.data.get("value")
        sensor_config = next(
            (s for s in SENSORS if s.get("unique_id") == sensor_name and s.get("writable")),
            None,
        )
        if not sensor_config:
            _LOGGER.error(
                f"Service 'write_register': Sensor '{sensor_name}' is not found or not writable."
            )
            return
        # Convert scaled value back to raw register value (e.g., 25.5°C -> 255)
        raw_value = int(value_to_write / sensor_config.get("scale", 1.0))
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


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.services.async_remove(DOMAIN, "write_register")
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class TECHeatPumpCoordinator(DataUpdateCoordinator):
    """Data coordinator for the TEC Heat Pump."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.host = entry.data[CONF_HOST]
        self.port = entry.data[CONF_PORT]
        self.device_id = entry.data[CONF_DEVICE_ID]
        self.timeout = entry.data[CONF_TIMEOUT]
        self.entry = entry
        device_name = entry.data.get(CONF_NAME, entry.title or DEFAULT_NAME)
        delay = entry.data.get(CONF_DELAY, DEFAULT_DELAY)
        update_interval = timedelta(seconds=delay)
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=device_name,
            manufacturer="TEC",
            model="Heat Pump",
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from API endpoint."""
        from pymodbus.client import ModbusTcpClient

        all_entities = SENSORS + SWITCHES
        data = {}
        client = ModbusTcpClient(host=self.host, port=self.port, timeout=self.timeout)

        try:
            if not await self.hass.async_add_executor_job(client.connect):
                raise UpdateFailed(f"Failed to connect to {self.host}:{self.port}")

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
            
            for (device_id, function_code), entities in entity_groups.items():
                modbus_func_map = {
                    1: client.read_coils,
                    2: client.read_discrete_inputs,
                    3: client.read_holding_registers,
                    4: client.read_input_registers,
                }
                read_func = modbus_func_map.get(function_code)
                if not read_func:
                    continue

                # Read all addresses in one batch for efficiency
                min_addr = min(s["address"] for s in entities)
                max_addr = max(s["address"] for s in entities)
                count = max_addr - min_addr + 1

                result = await self.hass.async_add_executor_job(
                    lambda: read_func(address=min_addr, count=count, device_id=device_id)
                )

                if result.isError():
                    _LOGGER.warning(f"Modbus error reading function {function_code}: {result}")
                    continue

                for entity in entities:
                    offset = entity["address"] - min_addr
                    value = None
                    if hasattr(result, "bits") and len(result.bits) > offset:
                        value = result.bits[offset]
                    elif hasattr(result, "registers") and len(result.registers) > offset:
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

        except Exception as e:
            raise UpdateFailed(f"Error communicating with device: {e}")
        finally:
            if client.is_socket_open():
                await self.hass.async_add_executor_job(client.close)

        return data

    async def api_write_register(self, address: int, value: int, device_id: int) -> None:
        """Write a single holding register."""
        from pymodbus.client import ModbusTcpClient

        client = ModbusTcpClient(host=self.host, port=self.port, timeout=self.timeout)
        try:
            if not await self.hass.async_add_executor_job(client.connect):
                raise UpdateFailed(f"Cannot connect to {self.host} to write register")

            result = await self.hass.async_add_executor_job(
                lambda: client.write_register(address=address, value=value, device_id=device_id)
            )
            if result.isError():
                _LOGGER.error("Failed to write register %s: %s", address, result)
                raise UpdateFailed("Failed to write register")
        finally:
            if client.is_socket_open():
                await self.hass.async_add_executor_job(client.close)

    async def write_coil(self, address: int, value: bool, device_id: int) -> None:
        """Write a single coil."""
        from pymodbus.client import ModbusTcpClient

        client = ModbusTcpClient(host=self.host, port=self.port, timeout=self.timeout)
        try:
            if not await self.hass.async_add_executor_job(client.connect):
                raise UpdateFailed(f"Cannot connect to {self.host} to write coil")

            result = await self.hass.async_add_executor_job(
                lambda: client.write_coil(address=address, value=value, device_id=device_id)
            )
            if result.isError():
                _LOGGER.error(f"Failed to write coil {address}: {result}")
                raise UpdateFailed("Failed to write coil")
        finally:
            if client.is_socket_open():
                await self.hass.async_add_executor_job(client.close)
