"""Tests for stitch show command."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from stitch.apps.operator.app import app
from stitch.core.queries import QueryResult

runner = CliRunner()


@patch("stitch.apps.operator.show.get_client")
def test_show_device_uri(mock_get):
    client = AsyncMock()
    client.query = AsyncMock(
        return_value=QueryResult(
            items=[{"id": "sw-core-01", "type": "SWITCH"}], total=1
        )
    )
    client.close = AsyncMock()
    mock_get.return_value = client
    result = runner.invoke(app, ["-o", "json", "show", "stitch:/device/sw-core-01"])
    assert result.exit_code == 0
    assert "sw-core-01" in result.stdout
    call_args = client.query.call_args
    assert call_args[0] == ("device", "show")
    assert call_args[1]["resource_id"] == "sw-core-01"


def test_show_invalid_uri():
    result = runner.invoke(app, ["-o", "json", "show", "not-a-uri"])
    assert result.exit_code != 0
