"""Tests for stitch run {list, show, watch, execute, cancel} commands."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from stitch.apps.operator.app import app
from stitch.core.queries import QueryResult

runner = CliRunner()

MOCK_RUNS = [
    {"run_id": "run_4f8a", "status": "running", "description": "preflight site-rdam"},
    {"run_id": "run_3e1b", "status": "succeeded", "description": "preflight site-ams"},
]


@patch("stitch.apps.operator.run_cmds.get_client")
def test_run_list(mock_get):
    client = AsyncMock()
    client.query = AsyncMock(return_value=QueryResult(items=MOCK_RUNS, total=2))
    client.close = AsyncMock()
    mock_get.return_value = client
    result = runner.invoke(app, ["-o", "json", "run", "list"])
    assert result.exit_code == 0
    assert "run_4f8a" in result.stdout


@patch("stitch.apps.operator.run_cmds.get_client")
def test_run_show(mock_get):
    client = AsyncMock()
    client.query = AsyncMock(return_value=QueryResult(items=[MOCK_RUNS[0]], total=1))
    client.close = AsyncMock()
    mock_get.return_value = client
    result = runner.invoke(app, ["-o", "json", "run", "show", "run_4f8a"])
    assert result.exit_code == 0
    assert "running" in result.stdout


@patch("stitch.apps.operator.run_cmds.get_client")
def test_run_watch_completed_skips_stream(mock_get):
    """When run is already terminal, watch just shows it without streaming."""
    client = AsyncMock()
    client.query = AsyncMock(
        return_value=QueryResult(
            items=[{"run_id": "run_3e1b", "status": "succeeded"}], total=1
        )
    )
    client.close = AsyncMock()
    mock_get.return_value = client
    result = runner.invoke(app, ["-o", "json", "run", "watch", "run_3e1b"])
    assert result.exit_code == 0
    assert "succeeded" in result.stdout


@patch("stitch.apps.operator.run_cmds.get_client")
def test_run_execute(mock_get):
    client = AsyncMock()
    client.command = AsyncMock(return_value={"run_id": "run_4f8a", "status": "running"})
    client.close = AsyncMock()
    mock_get.return_value = client
    result = runner.invoke(app, ["-o", "json", "run", "execute", "run_4f8a"])
    assert result.exit_code == 0
    assert "run_4f8a" in result.stdout


@patch("stitch.apps.operator.run_cmds.get_client")
def test_run_cancel(mock_get):
    client = AsyncMock()
    client.command = AsyncMock(return_value={"run_id": "run_4f8a", "status": "cancelled"})
    client.close = AsyncMock()
    mock_get.return_value = client
    result = runner.invoke(app, ["-o", "json", "run", "cancel", "run_4f8a"])
    assert result.exit_code == 0
    assert "cancelled" in result.stdout


@patch("stitch.apps.operator.run_cmds.get_client")
def test_run_cancel_with_reason(mock_get):
    client = AsyncMock()
    client.command = AsyncMock(return_value={"run_id": "run_4f8a", "status": "cancelled"})
    client.close = AsyncMock()
    mock_get.return_value = client
    result = runner.invoke(
        app, ["-o", "json", "run", "cancel", "run_4f8a", "--reason", "manual abort"]
    )
    assert result.exit_code == 0
    call_args = client.command.call_args
    assert call_args[1]["params"]["reason"] == "manual abort"
