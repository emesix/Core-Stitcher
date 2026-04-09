"""Tests for stitch trace run command."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from stitch.apps.operator.app import app

runner = CliRunner()

MOCK_TRACE = {
    "vlan": 42,
    "source": "sw-core-01",
    "status": "complete",
    "hops": [
        {"device": "sw-core-01", "port": "sfp-0", "status": "ok"},
        {"device": "fw-main", "port": "igb0", "status": "ok"},
    ],
}


@patch("stitch.apps.operator.trace.get_client")
def test_trace_run(mock_get):
    client = AsyncMock()
    client.command = AsyncMock(return_value=MOCK_TRACE)
    client.close = AsyncMock()
    mock_get.return_value = client
    result = runner.invoke(app, ["-o", "json", "trace", "run", "42", "--from", "sw-core-01"])
    assert result.exit_code == 0
    assert "complete" in result.stdout
    client.command.assert_awaited_once()
    call_args = client.command.call_args
    assert call_args[0] == ("trace", "run")
    assert call_args[1]["params"]["vlan"] == 42
    assert call_args[1]["params"]["source"] == "sw-core-01"


@patch("stitch.apps.operator.trace.get_client")
def test_trace_run_with_target(mock_get):
    client = AsyncMock()
    client.command = AsyncMock(return_value=MOCK_TRACE)
    client.close = AsyncMock()
    mock_get.return_value = client
    result = runner.invoke(
        app, ["-o", "json", "trace", "run", "42", "--from", "sw-core-01", "--to", "fw-main"]
    )
    assert result.exit_code == 0
    call_args = client.command.call_args
    assert call_args[1]["params"]["target"] == "fw-main"
