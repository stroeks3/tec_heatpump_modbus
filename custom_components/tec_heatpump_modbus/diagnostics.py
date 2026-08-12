"""Diagnostics support for TEC Heat Pump Modbus.

Provides the standard Home Assistant "Download diagnostics" payload for a
config entry: connection status, coordinator health and a full dump of all
known registers with their current (scaled) values. Host details are
redacted so the file is safe to attach to GitHub issues.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import DOMAIN, BINARY_SENSORS, NUMBERS, SENSORS, SWITCHES

TO_REDACT = {CONF_HOST}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}

    def describe(definitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "unique_id": d["unique_id"],
                "name": d.get("name"),
                "address": d.get("address"),
                "function": d.get("function") or d.get("register_type"),
                "scale": d.get("scale"),
                "unit": d.get("unit"),
                "writable": d.get("writable", False),
                "current_value": data.get(d["unique_id"]),
            }
            for d in definitions
        ]

    return {
        "config_entry": async_redact_data(dict(entry.data), TO_REDACT),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
            "modbus_connected": coordinator.client_connected,
            "device_id": coordinator.device_id,
        },
        "registers": {
            "numbers": describe(NUMBERS),
            "sensors": describe(SENSORS),
            "binary_sensors": describe(BINARY_SENSORS),
            "switches": describe(SWITCHES),
        },
    }
