"""Fixtures for the TEC Heat Pump Modbus test suite."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for every test (required by HA test harness)."""
    yield


@pytest.fixture
def mock_modbus_client():
    """Mock pymodbus' ModbusTcpClient so no real socket is opened.

    By default connect() succeeds and every read returns a non-error result
    with all-zero registers/bits, which is enough for the config flow's
    connectivity probe and the coordinator's first refresh.
    """
    with patch("pymodbus.client.ModbusTcpClient") as client_cls:
        client = MagicMock()
        client.connect.return_value = True
        client.is_socket_open.return_value = True

        def _ok_result(**kwargs):
            result = MagicMock()
            result.isError.return_value = False
            count = kwargs.get("count", 1)
            result.registers = [0] * count
            result.bits = [False] * count
            return result

        client.read_coils.side_effect = _ok_result
        client.read_discrete_inputs.side_effect = _ok_result
        client.read_holding_registers.side_effect = _ok_result
        client.read_input_registers.side_effect = _ok_result

        def _ok_write(**kwargs):
            result = MagicMock()
            result.isError.return_value = False
            return result

        client.write_register.side_effect = _ok_write
        client.write_coil.side_effect = _ok_write

        client_cls.return_value = client
        yield client
