"""Tests for the order of service registration against the platforms."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.tec_heatpump_modbus import async_setup_entry, async_unload_entry


def _hass(order):
    hass = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(
        side_effect=lambda *a, **k: order.append("platforms up")
    )
    hass.services.async_register = MagicMock(side_effect=lambda *a, **k: order.append("service up"))
    return hass


def test_the_service_is_up_before_the_platforms() -> None:
    """The AC switch returning triggers automations; the service must exist by then."""
    order: list[str] = []
    hass = _hass(order)
    with patch("custom_components.tec_heatpump_modbus.TECHeatPumpCoordinator") as coordinator:
        coordinator.return_value.async_config_entry_first_refresh = AsyncMock()
        assert asyncio.run(async_setup_entry(hass, MagicMock())) is True
    assert order == ["service up", "platforms up"]


def test_no_service_is_registered_when_the_first_refresh_fails() -> None:
    order: list[str] = []
    hass = _hass(order)
    with patch("custom_components.tec_heatpump_modbus.TECHeatPumpCoordinator") as coordinator:
        coordinator.return_value.async_config_entry_first_refresh = AsyncMock(
            side_effect=RuntimeError("unreachable")
        )
        try:
            asyncio.run(async_setup_entry(hass, MagicMock()))
        except RuntimeError:
            pass
    assert order == []


def test_the_service_goes_after_the_platforms_on_unload() -> None:
    order: list[str] = []
    hass = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(
        side_effect=lambda *a, **k: order.append("platforms down") or True
    )
    hass.services.async_remove = MagicMock(side_effect=lambda *a, **k: order.append("service down"))
    entry = MagicMock()
    entry.runtime_data.async_close = AsyncMock()
    assert asyncio.run(async_unload_entry(hass, entry)) is True
    assert order == ["platforms down", "service down"]
    entry.runtime_data.async_close.assert_awaited_once()


def test_a_failed_unload_keeps_the_service() -> None:
    hass = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)
    entry = MagicMock()
    entry.runtime_data.async_close = AsyncMock()
    assert asyncio.run(async_unload_entry(hass, entry)) is False
    hass.services.async_remove.assert_not_called()
    entry.runtime_data.async_close.assert_not_awaited()
