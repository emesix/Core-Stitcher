"""Tests for stitch impact {preview} commands."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from stitch.apps.operator.app import app

runner = CliRunner()


@patch("stitch.apps.operator.impact.get_client")
def test_impact_preview(mock_get):
    client = AsyncMock()
    client.command = AsyncMock(
        return_value={"affected_vlans": [100, 200], "affected_devices": ["sw-core-01"]}
    )
    client.close = AsyncMock()
    mock_get.return_value = client
    result = runner.invoke(
        app,
        [
            "-o", "json",
            "impact", "preview",
            "--action", "disable",
            "--device", "sw-core-01",
            "--port", "port1",
        ],
    )
    assert result.exit_code == 0
    assert "affected_vlans" in result.stdout
    call_args = client.command.call_args
    assert call_args[1]["params"]["action"] == "disable"
    assert call_args[1]["params"]["device"] == "sw-core-01"
    assert call_args[1]["params"]["port"] == "port1"
