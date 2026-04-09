"""Tests for stitch preflight run command."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from stitch.apps.operator.app import app

runner = CliRunner()

MOCK_REPORT = {
    "timestamp": "2026-04-09T12:00:00",
    "results": [],
    "summary": {"total": 16, "ok": 14, "warning": 1, "error": 1},
}


@patch("stitch.apps.operator.preflight.get_client")
def test_preflight_run(mock_get):
    client = AsyncMock()
    client.command = AsyncMock(return_value=MOCK_REPORT)
    client.close = AsyncMock()
    mock_get.return_value = client
    result = runner.invoke(app, ["-o", "json", "preflight", "run"])
    assert result.exit_code == 0
    assert "summary" in result.stdout
    client.command.assert_awaited_once()


@patch("stitch.apps.operator.preflight.get_client")
def test_preflight_run_with_scope(mock_get):
    client = AsyncMock()
    client.command = AsyncMock(return_value=MOCK_REPORT)
    client.close = AsyncMock()
    mock_get.return_value = client
    result = runner.invoke(app, ["-o", "json", "preflight", "run", "--scope", "vlans"])
    assert result.exit_code == 0
    call_args = client.command.call_args
    assert call_args[1]["params"]["scope"] == "vlans"


@patch("stitch.apps.operator.preflight.get_client")
def test_preflight_run_watch_stub(mock_get):
    client = AsyncMock()
    client.command = AsyncMock(return_value=MOCK_REPORT)
    client.close = AsyncMock()
    mock_get.return_value = client
    result = runner.invoke(app, ["-o", "json", "preflight", "run", "--watch"])
    assert result.exit_code == 0
    assert "summary" in result.stdout
