"""Tests for setup/unload, the write_register service, and the coordinator."""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry
from homeassistant.helpers import issue_registry as ir
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


async def test_climate_and_water_heater_are_created(hass: HomeAssistant, mock_modbus_client) -> None:
    """The two bundled entities exist on the same device as the rest."""
    entry = await _setup_entry(hass)
    registry = entity_registry.async_get(hass)
    assert registry.async_get_entity_id("climate", DOMAIN, f"{entry.entry_id}_climate")
    assert registry.async_get_entity_id("water_heater", DOMAIN, f"{entry.entry_id}_water_heater")
    assert await hass.config_entries.async_unload(entry.entry_id)


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

def _holding_registers(values: dict[int, int]):
    """A read_holding_registers stand-in answering from an address -> raw map."""

    def _read(**kwargs):
        result = MagicMock()
        result.isError.return_value = False
        start, count = kwargs["address"], kwargs.get("count", 1)
        result.registers = [values.get(start + i, 0) for i in range(count)]
        return result

    return _read


async def _breach(hass: HomeAssistant, mock_modbus_client):
    """Set up with every holding register at 0 (EV06, CM16, CM13 all under their
    floors), then age the debounce timers so one more poll reports them."""
    entry = await _setup_entry(hass)
    coordinator = entry.runtime_data
    for key in coordinator._below_since:
        coordinator._below_since[key] -= 400
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    return entry, coordinator


async def test_floor_breach_raises_repairs_notices_and_the_sensor(
    hass: HomeAssistant, mock_modbus_client
) -> None:
    """Registers under their floors for the debounce period raise Repairs notices
    and switch the Safety Floor Breach sensor on; the inverter alarm stays quiet."""
    entry, _ = await _breach(hass, mock_modbus_client)

    registry = ir.async_get(hass)
    for issue_id in ("floor_ev06", "floor_cm16", "floor_cm13"):
        issue = registry.async_get_issue(DOMAIN, f"{entry.entry_id}_{issue_id}")
        assert issue is not None, issue_id
        assert issue.is_fixable is False
    assert registry.async_get_issue(DOMAIN, f"{entry.entry_id}_inverter_alarm") is None

    entity_id = entity_registry.async_get(hass).async_get_entity_id(
        "binary_sensor", DOMAIN, f"{entry.entry_id}_safety_floor_breach"
    )
    assert hass.states.get(entity_id).state == "on"


async def test_floor_notices_clear_when_the_registers_are_back(
    hass: HomeAssistant, mock_modbus_client
) -> None:
    """Writing the registers back to or above their floors takes the notices down."""
    entry, coordinator = await _breach(hass, mock_modbus_client)

    # EV06 raw 230 = 23.0 %, CM16 and CM13 = 30 Hz.
    mock_modbus_client.read_holding_registers.side_effect = _holding_registers(
        {21: 230, 121: 30, 122: 30}
    )
    coordinator.force_slow_read()
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    registry = ir.async_get(hass)
    for issue_id in ("floor_ev06", "floor_cm16", "floor_cm13"):
        assert registry.async_get_issue(DOMAIN, f"{entry.entry_id}_{issue_id}") is None
    entity_id = entity_registry.async_get(hass).async_get_entity_id(
        "binary_sensor", DOMAIN, f"{entry.entry_id}_safety_floor_breach"
    )
    assert hass.states.get(entity_id).state == "off"


async def test_removing_the_entry_removes_its_notices(
    hass: HomeAssistant, mock_modbus_client
) -> None:
    entry, _ = await _breach(hass, mock_modbus_client)
    registry = ir.async_get(hass)
    assert registry.async_get_issue(DOMAIN, f"{entry.entry_id}_floor_ev06") is not None

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert registry.async_get_issue(DOMAIN, f"{entry.entry_id}_floor_ev06") is None


async def test_the_service_exists_while_the_platforms_come_up(
    hass: HomeAssistant, mock_modbus_client
) -> None:
    """Against a real instance: an entity that returns must find write_register."""
    seen: dict[str, bool] = {}
    original = hass.config_entries.async_forward_entry_setups

    async def spy(entry, platforms):
        seen["registered"] = hass.services.has_service(DOMAIN, "write_register")
        return await original(entry, platforms)

    with patch.object(hass.config_entries, "async_forward_entry_setups", spy):
        entry = await _setup_entry(hass)

    assert seen["registered"] is True
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert not hass.services.has_service(DOMAIN, "write_register")


async def test_a_reload_keeps_the_service_while_the_entities_return(
    hass: HomeAssistant, mock_modbus_client
) -> None:
    """The case behind the fix: reload, and watch the service at platform setup."""
    entry = await _setup_entry(hass)
    seen: dict[str, bool] = {}
    original = hass.config_entries.async_forward_entry_setups

    async def spy(e, platforms):
        seen["registered"] = hass.services.has_service(DOMAIN, "write_register")
        return await original(e, platforms)

    with patch.object(hass.config_entries, "async_forward_entry_setups", spy):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    assert seen["registered"] is True
    assert hass.services.has_service(DOMAIN, "write_register")
