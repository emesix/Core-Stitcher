"""Tests for stitch review {show, list, request, approve, reject} commands."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from stitch.apps.operator.app import app
from stitch.core.queries import QueryResult

runner = CliRunner()

MOCK_RUNS = [
    {"run_id": "run_4f8a", "status": "pending_review", "description": "preflight site-rdam"},
]


def _mock_client(query_result=None, command_result=None):
    client = AsyncMock()
    client.query = AsyncMock(
        return_value=query_result or QueryResult(items=MOCK_RUNS, total=1)
    )
    client.command = AsyncMock(return_value=command_result or {})
    client.close = AsyncMock()
    return client


@patch("stitch.apps.operator.review.get_client")
def test_review_show(mock_get):
    mock_get.return_value = _mock_client()
    result = runner.invoke(app, ["-o", "json", "review", "show", "run_4f8a"])
    assert result.exit_code == 0
    assert "run_4f8a" in result.stdout


@patch("stitch.apps.operator.review.get_client")
def test_review_list(mock_get):
    mock_get.return_value = _mock_client()
    result = runner.invoke(app, ["-o", "json", "review", "list"])
    assert result.exit_code == 0
    assert "run_4f8a" in result.stdout


@patch("stitch.apps.operator.review.get_client")
def test_review_request(mock_get):
    mock_get.return_value = _mock_client(
        command_result={"run_id": "run_4f8a", "status": "pending_review"}
    )
    result = runner.invoke(app, ["-o", "json", "review", "request", "run_4f8a"])
    assert result.exit_code == 0
    assert "pending_review" in result.stdout


@patch("stitch.apps.operator.review.get_client")
def test_review_approve_with_yes(mock_get):
    mock_get.return_value = _mock_client(
        command_result={"run_id": "run_4f8a", "status": "approved"}
    )
    result = runner.invoke(app, ["-o", "json", "--yes", "review", "approve", "run_4f8a"])
    assert result.exit_code == 0
    assert "approved" in result.stdout
    call_args = mock_get.return_value.command.call_args
    assert call_args[1]["params"]["action"] == "approve"


@patch("stitch.apps.operator.review.get_client")
def test_review_approve_with_comment(mock_get):
    mock_get.return_value = _mock_client(
        command_result={"run_id": "run_4f8a", "status": "approved"}
    )
    result = runner.invoke(
        app,
        ["-o", "json", "--yes", "review", "approve", "run_4f8a", "--comment", "looks good"],
    )
    assert result.exit_code == 0
    call_args = mock_get.return_value.command.call_args
    assert call_args[1]["params"]["comment"] == "looks good"


@patch("stitch.apps.operator.review.get_client")
def test_review_reject_with_yes(mock_get):
    mock_get.return_value = _mock_client(
        command_result={"run_id": "run_4f8a", "status": "rejected"}
    )
    result = runner.invoke(app, ["-o", "json", "--yes", "review", "reject", "run_4f8a"])
    assert result.exit_code == 0
    assert "rejected" in result.stdout
    call_args = mock_get.return_value.command.call_args
    assert call_args[1]["params"]["action"] == "reject"


@patch("stitch.apps.operator.review.get_client")
def test_review_approve_requires_confirmation(mock_get):
    """Without --yes, approve should prompt and abort when input is 'n'."""
    mock_get.return_value = _mock_client(
        command_result={"run_id": "run_4f8a", "status": "approved"}
    )
    result = runner.invoke(app, ["-o", "json", "review", "approve", "run_4f8a"], input="n\n")
    assert result.exit_code != 0
