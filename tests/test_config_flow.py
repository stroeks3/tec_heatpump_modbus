"""Tests for the TEC Heat Pump Modbus config flow."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tec_heatpump_modbus.const import (
    CONF_CLIMATE_WRITES,
    CONF_DELAY,
    CONF_DEVICE_ID,
    CONF_NAME,
    CONF_TIMEOUT,
    CONF_WATER_HEATER_WRITES,
    DEFAULT_NAME,
    DOMAIN,
)

USER_INPUT = {
    CONF_HOST: "192.168.1.178",
    CONF_PORT: 502,
    CONF_DEVICE_ID: 9,
    CONF_DELAY: 5,
    CONF_TIMEOUT: 5,
}


async def test_user_flow_success(hass: HomeAssistant, mock_modbus_client) -> None:
    """A valid host/device_id creates a config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    # The name field is optional in the schema and carries a default, so the stored
    # entry holds one more key than was submitted.
    assert result["data"] == {**USER_INPUT, CONF_NAME: DEFAULT_NAME}


async def test_user_flow_cannot_connect(hass: HomeAssistant, mock_modbus_client) -> None:
    """A socket that never connects shows the cannot_connect error."""
    mock_modbus_client.connect.return_value = False

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_invalid_device_id(hass: HomeAssistant, mock_modbus_client) -> None:
    """A Modbus error response on the probe read shows invalid_device_id."""
    error_result = MagicMock()
    error_result.isError.return_value = True
    mock_modbus_client.read_coils.side_effect = None
    mock_modbus_client.read_coils.return_value = error_result

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_device_id"}


async def test_duplicate_entry_aborts(hass: HomeAssistant, mock_modbus_client) -> None:
    """The same host + device_id combination cannot be configured twice."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{USER_INPUT[CONF_HOST]}_{USER_INPUT[CONF_DEVICE_ID]}",
        data=USER_INPUT,
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_stores_writes_and_polling(hass: HomeAssistant, mock_modbus_client) -> None:
    """The options flow stores delay, timeout and the two write switches."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{USER_INPUT[CONF_HOST]}_{USER_INPUT[CONF_DEVICE_ID]}",
        data=USER_INPUT,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_DELAY: 10, CONF_TIMEOUT: 5, CONF_CLIMATE_WRITES: False, CONF_WATER_HEATER_WRITES: True},
    )
    await hass.async_block_till_done()
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_CLIMATE_WRITES] is False
    assert entry.options[CONF_DELAY] == 10
    # The reload picked the new interval up.
    assert entry.runtime_data.update_interval.total_seconds() == 10


async def test_reconfigure_updates_host_and_unique_id(hass: HomeAssistant, mock_modbus_client) -> None:
    """A moved gateway keeps its entry; the unique id follows the host."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{USER_INPUT[CONF_HOST]}_{USER_INPUT[CONF_DEVICE_ID]}",
        data=USER_INPUT,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.168.1.200", CONF_PORT: 502, CONF_DEVICE_ID: 9}
    )
    await hass.async_block_till_done()
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_HOST] == "192.168.1.200"
    assert entry.unique_id == "192.168.1.200_9"
