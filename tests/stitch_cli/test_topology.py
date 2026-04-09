"""Tests for stitch topology {show, diagnostics, export, diff} commands."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from stitch.apps.operator.app import app
from stitch.core.queries import QueryResult

runner = CliRunner()

MOCK_TOPOLOGY = [{"id": "topo_01", "name": "lab-rdam", "devices": 4, "links": 6}]


def _mock_client(query_result=None, command_result=None):
    client = AsyncMock()
    client.query = AsyncMock(
        return_value=query_result or QueryResult(items=MOCK_TOPOLOGY, total=1)
    )
    client.command = AsyncMock(return_value=command_result or {})
    client.close = AsyncMock()
    return client


@patch("stitch.apps.operator.topology.get_client")
def test_topology_show(mock_get):
    mock_get.return_value = _mock_client()
    result = runner.invoke(app, ["-o", "json", "topology", "show"])
    assert result.exit_code == 0
    assert "lab-rdam" in result.stdout


@patch("stitch.apps.operator.topology.get_client")
def test_topology_diagnostics(mock_get):
    diag = [{"check": "link_count", "status": "ok"}]
    mock_get.return_value = _mock_client(QueryResult(items=diag, total=1))
    result = runner.invoke(app, ["-o", "json", "topology", "diagnostics"])
    assert result.exit_code == 0
    assert "link_count" in result.stdout


@patch("stitch.apps.operator.topology.get_client")
def test_topology_export_json(mock_get):
    mock_get.return_value = _mock_client()
    result = runner.invoke(app, ["-o", "json", "topology", "export", "--format", "json"])
    assert result.exit_code == 0
    assert "lab-rdam" in result.stdout


@patch("stitch.apps.operator.topology.get_client")
def test_topology_export_yaml(mock_get):
    mock_get.return_value = _mock_client()
    result = runner.invoke(app, ["-o", "yaml", "topology", "export", "--format", "yaml"])
    assert result.exit_code == 0
    assert "lab-rdam" in result.stdout


@patch("stitch.apps.operator.topology.get_client")
def test_topology_diff(mock_get):
    diff_result = {"added": 1, "removed": 0, "changed": 2}
    mock_get.return_value = _mock_client(command_result=diff_result)
    result = runner.invoke(app, ["-o", "json", "topology", "diff", "snap_01", "snap_02"])
    assert result.exit_code == 0
    assert "added" in result.stdout
    call_args = mock_get.return_value.command.call_args
    assert call_args[1]["params"]["before"] == "snap_01"
    assert call_args[1]["params"]["after"] == "snap_02"
