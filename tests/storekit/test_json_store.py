"""Tests for JSON file store — save, load, list, delete, roundtrip."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from vos.agentcore.plannerkit import SubtaskSpec, WorkRequest, plan_request
from vos.agentcore.reviewkit import ReviewFinding, ReviewResult, ReviewVerdict, Severity
from vos.agentcore.storekit import JsonRunStore, RunRecord, RunStatus, RunStore, TaskExecution
from vos.agentcore.taskkit import TaskOutcome, TaskStatus


@pytest.fixture()
def store(tmp_path: Path) -> JsonRunStore:
    return JsonRunStore(tmp_path / "runs")


def _minimal_run() -> RunRecord:
    return RunRecord(request=WorkRequest(description="test"))


# --- Protocol compliance ---


def test_implements_protocol(store: JsonRunStore):
    assert isinstance(store, RunStore)


# --- Save and get ---


def test_save_and_get(store: JsonRunStore):
    run = _minimal_run()
    store.save(run)
    loaded = store.get(run.run_id)
    assert loaded is not None
    assert loaded.run_id == run.run_id
    assert loaded.request.description == "test"


def test_get_nonexistent(store: JsonRunStore):
    assert store.get(uuid4()) is None


def test_save_overwrites(store: JsonRunStore):
    run = _minimal_run()
    store.save(run)
    run.status = RunStatus.COMPLETED
    store.save(run)
    loaded = store.get(run.run_id)
    assert loaded.status == RunStatus.COMPLETED


# --- List ---


def test_list_empty(store: JsonRunStore):
    assert store.list_runs() == []


def test_list_multiple(store: JsonRunStore):
    for _ in range(3):
        store.save(_minimal_run())
    runs = store.list_runs()
    assert len(runs) == 3


# --- Delete ---


def test_delete(store: JsonRunStore):
    run = _minimal_run()
    store.save(run)
    assert store.delete(run.run_id) is True
    assert store.get(run.run_id) is None


def test_delete_nonexistent(store: JsonRunStore):
    assert store.delete(uuid4()) is False


# --- Full pipeline roundtrip ---


def test_full_run_roundtrip(store: JsonRunStore):
    request = WorkRequest(
        description="verify topology",
        domain="topology",
        subtasks=[SubtaskSpec(description="collect"), SubtaskSpec(description="verify")],
    )
    plan = plan_request(request)

    run = RunRecord(
        status=RunStatus.COMPLETED,
        request=request,
        plan=plan,
        executions=[
            TaskExecution(
                task_id=plan.tasks[1].task_id,
                description="collect",
                domain="topology",
                executor_id="mock-1",
                outcome=TaskOutcome(status=TaskStatus.COMPLETED, result="done"),
            ),
            TaskExecution(
                task_id=plan.tasks[2].task_id,
                description="verify",
                domain="topology",
                executor_id="mock-1",
                outcome=TaskOutcome(status=TaskStatus.COMPLETED, result="verified"),
            ),
        ],
        reviews=[
            ReviewResult(
                verdict=ReviewVerdict.APPROVE,
                findings=[
                    ReviewFinding(description="all good", severity=Severity.INFO),
                ],
                summary="approved",
            ),
        ],
    )

    store.save(run)
    loaded = store.get(run.run_id)

    assert loaded.status == RunStatus.COMPLETED
    assert loaded.request.description == "verify topology"
    assert len(loaded.plan.tasks) == 3
    assert len(loaded.executions) == 2
    assert loaded.executions[0].outcome.status == TaskStatus.COMPLETED
    assert len(loaded.reviews) == 1
    assert loaded.reviews[0].verdict == ReviewVerdict.APPROVE


# --- Corrupt file handling ---


def test_corrupt_file_skipped_in_list(store: JsonRunStore):
    store.save(_minimal_run())
    (store._dir / "bad.json").write_text("not valid json{{{")
    runs = store.list_runs()
    assert len(runs) == 1


# --- Directory creation ---


def test_creates_directory(tmp_path: Path):
    path = tmp_path / "new" / "nested" / "runs"
    s = JsonRunStore(path)
    s.save(_minimal_run())
    assert path.exists()
    assert len(s.list_runs()) == 1
