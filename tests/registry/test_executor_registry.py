"""Tests for executor registry — registration, lookup, domain matching, health filtering."""

from __future__ import annotations

import pytest

from stitch.agentcore.executorkit import ExecutorCapability, ExecutorHealth, ExecutorProtocol
from stitch.agentcore.registry import ExecutorRegistry
from stitch.agentcore.registry.executor_registry import ExecutorNotFoundError
from stitch.agentcore.taskkit import TaskOutcome, TaskRecord, TaskStatus


class FakeExecutor:
    def __init__(
        self,
        executor_id: str = "fake-1",
        domains: list[str] | None = None,
        health_status: str = "ok",
    ) -> None:
        self._id = executor_id
        self._capability = ExecutorCapability(domains=domains or [])
        self._health_status = health_status

    @property
    def executor_id(self) -> str:
        return self._id

    @property
    def capability(self) -> ExecutorCapability:
        return self._capability

    async def execute(self, task: TaskRecord) -> TaskOutcome:
        return TaskOutcome(status=TaskStatus.COMPLETED, executor_id=self._id)

    async def health(self) -> ExecutorHealth:
        return ExecutorHealth(status=self._health_status)


def test_register_and_get():
    reg = ExecutorRegistry()
    ex = FakeExecutor("ex-1")
    reg.register(ex)
    assert reg.get("ex-1") is ex


def test_get_not_found():
    reg = ExecutorRegistry()
    with pytest.raises(ExecutorNotFoundError):
        reg.get("nonexistent")


def test_unregister():
    reg = ExecutorRegistry()
    ex = FakeExecutor("ex-1")
    reg.register(ex)
    reg.unregister("ex-1")
    assert len(reg) == 0


def test_unregister_nonexistent():
    reg = ExecutorRegistry()
    reg.unregister("nonexistent")  # Should not raise


def test_list_all():
    reg = ExecutorRegistry()
    reg.register(FakeExecutor("a"))
    reg.register(FakeExecutor("b"))
    assert len(reg.list_all()) == 2


def test_len():
    reg = ExecutorRegistry()
    assert len(reg) == 0
    reg.register(FakeExecutor("a"))
    assert len(reg) == 1


def test_find_for_task_no_domain():
    reg = ExecutorRegistry()
    reg.register(FakeExecutor("a", domains=["topology"]))
    reg.register(FakeExecutor("b", domains=["research"]))

    # Task with no domain matches all executors
    task = TaskRecord(description="generic task")
    matches = reg.find_for_task(task)
    assert len(matches) == 2


def test_find_for_task_with_domain():
    reg = ExecutorRegistry()
    reg.register(FakeExecutor("topo", domains=["topology"]))
    reg.register(FakeExecutor("research", domains=["research"]))
    reg.register(FakeExecutor("general"))  # No domains = matches anything

    task = TaskRecord(description="verify topology", domain="topology")
    matches = reg.find_for_task(task)
    ids = {m.executor_id for m in matches}
    assert ids == {"topo", "general"}


def test_find_for_task_no_matches():
    reg = ExecutorRegistry()
    reg.register(FakeExecutor("research", domains=["research"]))

    task = TaskRecord(description="x", domain="topology")
    matches = reg.find_for_task(task)
    assert matches == []


async def test_healthy_executors():
    reg = ExecutorRegistry()
    reg.register(FakeExecutor("ok-1", health_status="ok"))
    reg.register(FakeExecutor("deg-1", health_status="degraded"))
    reg.register(FakeExecutor("err-1", health_status="error"))

    healthy = await reg.healthy_executors()
    ids = {ex.executor_id for ex, _h in healthy}
    assert ids == {"ok-1", "deg-1"}


async def test_healthy_executors_empty():
    reg = ExecutorRegistry()
    healthy = await reg.healthy_executors()
    assert healthy == []


def test_protocol_compliance():
    ex = FakeExecutor()
    assert isinstance(ex, ExecutorProtocol)
