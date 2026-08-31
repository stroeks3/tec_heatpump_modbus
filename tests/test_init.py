"""Tests for setup/unload, the write_register service, and the coordinator."""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tec_heatpump_modbus.const import (
    CONF_DELAY,
    CONF_DEVICE_ID,
    CONF_TIMEOUT,
    DOMAIN,
)

ENTRY_DATA = {
    CONF_HOST: "192.168.1.178",
    CONF_PORT: 502,
    CONF_DEVICE_ID: 9,
    CONF_DELAY: 5,
    CONF_TIMEOUT: 5,
}


async def _setup_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{ENTRY_DATA[CONF_HOST]}_{ENTRY_DATA[CONF_DEVICE_ID]}",
        data=ENTRY_DATA,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_setup_and_unload_entry(hass: HomeAssistant, mock_modbus_client) -> None:
    """Setup stores the coordinator on runtime_data; unload closes the client."""
    entry = await _setup_entry(hass)

    assert entry.state is ConfigEntryState.LOADED
    coordinator = entry.runtime_data
    assert coordinator.last_update_success is True
    assert hass.services.has_service(DOMAIN, "write_register")

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not hass.services.has_service(DOMAIN, "write_register")
    mock_modbus_client.close.assert_called()


async def test_setup_entry_not_ready_when_unreachable(
    hass: HomeAssistant, mock_modbus_client
) -> None:
    """Setup retries instead of loading when the device never connects."""
    # Both are needed: the coordinator only calls connect() when the socket is
    # closed, so leaving is_socket_open at the fixture default of True would skip
    # the connection attempt entirely and the reads would still succeed.
    mock_modbus_client.connect.return_value = False
    mock_modbus_client.is_socket_open.return_value = False

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{ENTRY_DATA[CONF_HOST]}_{ENTRY_DATA[CONF_DEVICE_ID]}",
        data=ENTRY_DATA,
    )
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_write_register_service_success(
    hass: HomeAssistant, mock_modbus_client
) -> None:
    """Writing a known writable register scales the value and hits Modbus."""
    await _setup_entry(hass)

    await hass.services.async_call(
        DOMAIN,
        "write_register",
        {"sensor": "st01", "value": 21.3},
        blocking=True,
    )

    mock_modbus_client.write_register.assert_called_once()
    _, kwargs = mock_modbus_client.write_register.call_args
    assert kwargs["address"] == 61
    assert kwargs["value"] == 213


async def test_write_register_service_invalid_sensor(
    hass: HomeAssistant, mock_modbus_client
) -> None:
    """An unknown/non-writable sensor name raises a user-facing error."""
    await _setup_entry(hass)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "write_register",
            {"sensor": "does_not_exist", "value": 1},
            blocking=True,
        )


async def test_read_errors_logged_only_once(
    hass: HomeAssistant, mock_modbus_client, caplog: pytest.LogCaptureFixture
) -> None:
    """A sustained read failure logs a warning once, not on every poll.

    Uses the INPUT registers deliberately. Holding registers sit on the slow
    cadence since 2026.08.07, so three refreshes inside a minute would only
    read them once and this test would pass for the wrong reason.
    """
    entry = await _setup_entry(hass)
    coordinator = entry.runtime_data

    error_result = MagicMock()
    error_result.isError.return_value = True
    mock_modbus_client.read_input_registers.side_effect = None
    mock_modbus_client.read_input_registers.return_value = error_result

    caplog.clear()
    with caplog.at_level(logging.WARNING):
        await coordinator.async_refresh()
        await coordinator.async_refresh()
        await coordinator.async_refresh()

    warnings = [r for r in caplog.records if "Modbus error reading function" in r.message]
    assert len(warnings) == 1


async def test_switch_write_failure_raises(hass: HomeAssistant, mock_modbus_client) -> None:
    """A failed coil write surfaces as an error instead of failing silently."""
    from homeassistant.exceptions import HomeAssistantError

    await _setup_entry(hass)

    error_result = MagicMock()
    error_result.isError.return_value = True
    mock_modbus_client.write_coil.side_effect = None
    mock_modbus_client.write_coil.return_value = error_result
    mock_modbus_client.read_coils.reset_mock()

    # Driven through the service rather than a hand-built entity: an entity created
    # outside a platform has no `platform`, and reading `self.name` on it raises
    # before the code under test is ever reached. The entity id is looked up rather
    # than hard-coded, since it is derived from the device name.
    registry = entity_registry.async_get(hass)
    entity_id = next(
        e.entity_id
        for e in registry.entities.values()
        if e.domain == "switch" and e.unique_id.endswith("_di4")
    )

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": entity_id}, blocking=True
        )

    # The refresh in `finally` must still run despite the raised error.
    assert mock_modbus_client.read_coils.called