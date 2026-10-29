"""Config flow for TEC Heat Pump Modbus integration."""
from __future__ import annotations
import logging
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_NAME, CONF_DELAY, CONF_TIMEOUT, CONF_DEVICE_ID,
    CONF_CLIMATE_WRITES, CONF_WATER_HEATER_WRITES,
    DEFAULT_NAME, DEFAULT_DELAY, DEFAULT_PORT, DEFAULT_TIMEOUT, DEFAULT_DEVICE_ID,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidDeviceId(HomeAssistantError):
    """Error to indicate there is an invalid device id."""


STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    vol.Required(CONF_DEVICE_ID, default=DEFAULT_DEVICE_ID): int,
    vol.Required(CONF_DELAY, default=DEFAULT_DELAY): int,
    vol.Required(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): int,
})

def sync_validate_connection(data: dict[str, Any]) -> None:
    """Synchronous function to test connection."""
    from pymodbus.client import ModbusTcpClient
    client = ModbusTcpClient(host=data[CONF_HOST], port=data[CONF_PORT], timeout=data[CONF_TIMEOUT])
    try:
        if not client.connect():
            raise CannotConnect
        # Test communication with device by reading a single coil
        result = client.read_coils(address=1, count=1, device_id=data[CONF_DEVICE_ID])
        if result.isError():
            raise InvalidDeviceId
    finally:
        if client.is_socket_open():
            client.close()


def _unique_id(data: dict[str, Any]) -> str:
    return f"{data[CONF_HOST]}_{data[CONF_DEVICE_ID]}"


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OptionsFlow:
        """Polling and write options, changeable without re-adding the entry."""
        return OptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                title = user_input.get(CONF_NAME, DEFAULT_NAME)
                await self.hass.async_add_executor_job(sync_validate_connection, user_input)
                await self.async_set_unique_id(_unique_id(user_input))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=title, data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidDeviceId:
                errors["base"] = "invalid_device_id"
        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Change host, port or device id of an existing entry.

        The unique id follows the host, so a moved gateway gets its unique id
        updated rather than refused: entity ids and history stay with the
        entry.
        """
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**entry.data, **user_input}
            try:
                await self.hass.async_add_executor_job(sync_validate_connection, data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidDeviceId:
                errors["base"] = "invalid_device_id"
            else:
                return self.async_update_reload_and_abort(
                    entry, data=data, unique_id=_unique_id(data)
                )
        schema = vol.Schema({
            vol.Required(CONF_HOST, default=entry.data[CONF_HOST]): str,
            vol.Required(CONF_PORT, default=entry.data.get(CONF_PORT, DEFAULT_PORT)): int,
            vol.Required(CONF_DEVICE_ID, default=entry.data.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID)): int,
        })
        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)


class OptionsFlow(config_entries.OptionsFlow):
    """Polling interval, timeout and the two setpoint-write switches."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        entry = self.config_entry
        current = {**entry.data, **entry.options}
        schema = vol.Schema({
            vol.Required(CONF_DELAY, default=current.get(CONF_DELAY, DEFAULT_DELAY)): vol.All(int, vol.Range(min=1)),
            vol.Required(CONF_TIMEOUT, default=current.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)): vol.All(int, vol.Range(min=1)),
            vol.Required(CONF_CLIMATE_WRITES, default=current.get(CONF_CLIMATE_WRITES, True)): bool,
            vol.Required(CONF_WATER_HEATER_WRITES, default=current.get(CONF_WATER_HEATER_WRITES, True)): bool,
        })
        return self.async_show_form(step_id="init", data_schema=schema)
