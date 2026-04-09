"""Tests for Project Explorer CLI."""

from __future__ import annotations

import json

import pytest

from stitch.agentcore.plannerkit import SubtaskSpec, WorkRequest, plan_request
from stitch.apps.project_stitcher.cli import _format_plan, main


def test_main_single_task(capsys):
    rc = main(["do something"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "do something" in out
    assert "[root]" in out


def test_main_with_domain(capsys):
    rc = main(["check topology", "--domain", "topology"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "(topology)" in out


def test_main_with_priority(capsys):
    rc = main(["urgent task", "--priority", "critical"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[critical]" in out


def test_main_with_subtasks(capsys):
    rc = main(["main task", "--subtask", "step A", "--subtask", "step B"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "step A" in out
    assert "step B" in out
    assert "Tasks: 3" in out  # root + 2 subtasks


def test_main_json_output(capsys):
    rc = main(["test task", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["request_description"] == "test task"
    assert len(data["tasks"]) == 1


def test_main_json_with_subtasks(capsys):
    rc = main(["pipeline", "--subtask", "a", "--subtask", "b", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["tasks"]) == 3


def test_execution_order_shown(capsys):
    rc = main(["pipeline", "--subtask", "first", "--subtask", "second"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Execution order:" in out
    assert "#1" in out
    assert "#2" in out
    assert "#3" in out


def test_format_plan_deterministic():
    req = WorkRequest(description="test", subtasks=[SubtaskSpec(description="child")])
    plan = plan_request(req)
    out1 = _format_plan(plan)
    out2 = _format_plan(plan)
    assert out1 == out2


def test_main_invalid_priority():
    with pytest.raises(SystemExit) as exc_info:
        main(["task", "--priority", "invalid"])
    assert exc_info.value.code == 2


def test_main_no_args():
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2
