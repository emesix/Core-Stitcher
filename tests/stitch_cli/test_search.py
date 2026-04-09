"""Tests for stitch search command."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from stitch.apps.operator.app import app
from stitch.core.queries import QueryResult

runner = CliRunner()

MOCK_DEVICES = [
    {"id": "dev_01", "name": "sw-core-01", "type": "SWITCH"},
    {"id": "dev_02", "name": "fw-main", "type": "FIREWALL"},
    {"id": "dev_03", "name": "sw-access-01", "type": "SWITCH"},
]


@patch("stitch.apps.operator.search.get_client")
def test_search_filters_by_text(mock_get):
    client = AsyncMock()
    client.query = AsyncMock(return_value=QueryResult(items=MOCK_DEVICES, total=3))
    client.close = AsyncMock()
    mock_get.return_value = client
    result = runner.invoke(app, ["-o", "json", "search", "sw-core"])
    assert result.exit_code == 0
    assert "sw-core-01" in result.stdout
    # Should not include fw-main
    assert "fw-main" not in result.stdout


@patch("stitch.apps.operator.search.get_client")
def test_search_respects_limit(mock_get):
    client = AsyncMock()
    client.query = AsyncMock(return_value=QueryResult(items=MOCK_DEVICES, total=3))
    client.close = AsyncMock()
    mock_get.return_value = client
    result = runner.invoke(app, ["-o", "json", "search", "sw", "--limit", "1"])
    assert result.exit_code == 0
    assert "sw-core-01" in result.stdout


@patch("stitch.apps.operator.search.get_client")
def test_search_no_match(mock_get):
    client = AsyncMock()
    client.query = AsyncMock(return_value=QueryResult(items=MOCK_DEVICES, total=3))
    client.close = AsyncMock()
    mock_get.return_value = client
    result = runner.invoke(app, ["-o", "json", "search", "nonexistent"])
    assert result.exit_code == 0
