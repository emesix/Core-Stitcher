"""Tests for taskkit models — task state shape and transitions."""

from __future__ import annotations

from uuid import UUID

from vos.agentcore.taskkit import TaskOutcome, TaskPriority, TaskRecord, TaskStatus


def test_task_defaults():
    t = TaskRecord(description="do something")
    assert t.status == TaskStatus.PENDING
    assert t.priority == TaskPriority.NORMAL
    assert isinstance(t.id, UUID)
    assert t.parent_id is None
    assert t.domain is None
    assert t.outcome is None
    assert t.metadata == {}


def test_task_with_domain_and_priority():
    t = TaskRecord(
        description="verify topology",
        domain="topology",
        priority=TaskPriority.HIGH,
    )
    assert t.domain == "topology"
    assert t.priority == TaskPriority.HIGH


def test_task_parent_child():
    parent = TaskRecord(description="main task")
    child = TaskRecord(description="subtask", parent_id=parent.id)
    assert child.parent_id == parent.id


def test_is_terminal():
    for status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
        t = TaskRecord(description="x", status=status)
        assert t.is_terminal() is True

    for status in (TaskStatus.PENDING, TaskStatus.RUNNING):
        t = TaskRecord(description="x", status=status)
        assert t.is_terminal() is False


def test_task_outcome():
    outcome = TaskOutcome(
        status=TaskStatus.COMPLETED,
        result={"answer": 42},
        executor_id="claude-1",
    )
    assert outcome.status == TaskStatus.COMPLETED
    assert outcome.result == {"answer": 42}
    assert outcome.error is None


def test_task_outcome_failure():
    outcome = TaskOutcome(
        status=TaskStatus.FAILED,
        error="timeout after 30s",
        executor_id="local-llm",
    )
    assert outcome.error == "timeout after 30s"
    assert outcome.result is None


def test_task_metadata():
    t = TaskRecord(
        description="research",
        metadata={"source": "user", "tags": ["urgent"]},
    )
    assert t.metadata["source"] == "user"


def test_task_serialization_roundtrip():
    t = TaskRecord(description="test roundtrip", domain="topology", priority=TaskPriority.CRITICAL)
    data = t.model_dump(mode="json")
    restored = TaskRecord.model_validate(data)
    assert restored.id == t.id
    assert restored.description == t.description
    assert restored.domain == t.domain
    assert restored.priority == TaskPriority.CRITICAL
