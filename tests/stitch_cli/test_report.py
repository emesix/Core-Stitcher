"""Tests for stitch report {show, diff} commands."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from stitch.apps.operator.app import app
from stitch.core.queries import QueryResult

runner = CliRunner()

MOCK_REPORT = [{"id": "rpt_01", "status": "pass", "checks": 12, "failures": 0}]


def _mock_client(query_result=None, command_result=None):
    client = AsyncMock()
    client.query = AsyncMock(
        return_value=query_result or QueryResult(items=MOCK_REPORT, total=1)
    )
    client.command = AsyncMock(return_value=command_result or {})
    client.close = AsyncMock()
    return client


@patch("stitch.apps.operator.report.get_client")
def test_report_show(mock_get):
    mock_get.return_value = _mock_client()
    result = runner.invoke(app, ["-o", "json", "report", "show", "rpt_01"])
    assert result.exit_code == 0
    assert "rpt_01" in result.stdout


@patch("stitch.apps.operator.report.get_client")
def test_report_diff(mock_get):
    diff_result = {"added": 2, "removed": 1}
    mock_get.return_value = _mock_client(command_result=diff_result)
    result = runner.invoke(app, ["-o", "json", "report", "diff", "rpt_01", "rpt_02"])
    assert result.exit_code == 0
    assert "added" in result.stdout
    call_args = mock_get.return_value.command.call_args
    assert call_args[1]["params"]["before"] == "rpt_01"
    assert call_args[1]["params"]["after"] == "rpt_02"
