"""Config flow for TEC Heat Pump Modbus integration."""
from __future__ import annotations
import logging
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_NAME, CONF_DELAY, CONF_TIMEOUT, CONF_DEVICE_ID,
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

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""
    VERSION = 1
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                title = user_input.get(CONF_NAME, DEFAULT_NAME)
                await self.hass.async_add_executor_job(sync_validate_connection, user_input)
                await self.async_set_unique_id(f"{user_input[CONF_HOST]}_{user_input[CONF_DEVICE_ID]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=title, data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidDeviceId:
                errors["base"] = "invalid_device_id"
        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)