"""Tests for stitch device {list, show, inspect} commands."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from stitch.apps.operator.app import app
from stitch.core.queries import QueryResult

runner = CliRunner()

MOCK_DEVICES = [
    {
        "id": "dev_01",
        "name": "sw-core-01",
        "type": "SWITCH",
        "model": "USW-Pro-48",
        "management_ip": "192.168.254.2",
    },
    {
        "id": "dev_02",
        "name": "fw-main",
        "type": "FIREWALL",
        "model": "OPNsense",
        "management_ip": "192.168.254.1",
    },
]


def _mock_client(query_result):
    client = AsyncMock()
    client.query = AsyncMock(return_value=query_result)
    client.command = AsyncMock(return_value={})
    client.close = AsyncMock()
    return client


@patch("stitch.apps.operator.device.get_client")
def test_device_list(mock_get):
    mock_get.return_value = _mock_client(QueryResult(items=MOCK_DEVICES, total=2))
    result = runner.invoke(app, ["-o", "json", "device", "list"])
    assert result.exit_code == 0
    assert "sw-core-01" in result.stdout
    assert "fw-main" in result.stdout


@patch("stitch.apps.operator.device.get_client")
def test_device_show(mock_get):
    mock_get.return_value = _mock_client(QueryResult(items=[MOCK_DEVICES[0]], total=1))
    result = runner.invoke(app, ["-o", "json", "device", "show", "sw-core-01"])
    assert result.exit_code == 0
    assert "sw-core-01" in result.stdout


@patch("stitch.apps.operator.device.get_client")
def test_device_inspect(mock_get):
    client = _mock_client(QueryResult(items=[MOCK_DEVICES[0]], total=1))
    client.query.side_effect = [
        QueryResult(items=[MOCK_DEVICES[0]], total=1),
        QueryResult(items=[{"device": "fw-main", "port": "igb0"}], total=1),
    ]
    mock_get.return_value = client
    result = runner.invoke(app, ["-o", "json", "device", "inspect", "sw-core-01"])
    assert result.exit_code == 0
    assert "sw-core-01" in result.stdout
