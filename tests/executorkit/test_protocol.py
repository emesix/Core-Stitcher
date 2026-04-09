"""Tests for executor protocol compliance and capability shape."""

from __future__ import annotations

from stitch.agentcore.executorkit import ExecutorCapability, ExecutorHealth, ExecutorProtocol
from stitch.agentcore.taskkit import TaskOutcome, TaskRecord, TaskStatus


class FakeExecutor:
    def __init__(self, executor_id: str = "fake-1", domains: list[str] | None = None) -> None:
        self._id = executor_id
        self._capability = ExecutorCapability(domains=domains or [])

    @property
    def executor_id(self) -> str:
        return self._id

    @property
    def capability(self) -> ExecutorCapability:
        return self._capability

    async def execute(self, task: TaskRecord) -> TaskOutcome:
        return TaskOutcome(status=TaskStatus.COMPLETED, result="done", executor_id=self._id)

    async def health(self) -> ExecutorHealth:
        return ExecutorHealth(status="ok")


def test_fake_implements_protocol():
    assert isinstance(FakeExecutor(), ExecutorProtocol)


def test_capability_defaults():
    cap = ExecutorCapability()
    assert cap.domains == []
    assert cap.max_concurrent == 1
    assert cap.supports_streaming is False
    assert cap.tags == []


def test_capability_with_domains():
    cap = ExecutorCapability(domains=["topology", "research"], max_concurrent=4)
    assert "topology" in cap.domains
    assert cap.max_concurrent == 4


def test_health_shape():
    h = ExecutorHealth(status="ok", latency_ms=42.5)
    assert h.status == "ok"
    assert h.latency_ms == 42.5
    assert h.message is None


def test_health_degraded():
    h = ExecutorHealth(status="degraded", message="high latency")
    assert h.status == "degraded"
    assert h.message == "high latency"


async def test_executor_execute():
    executor = FakeExecutor()
    task = TaskRecord(description="test task")
    outcome = await executor.execute(task)
    assert outcome.status == TaskStatus.COMPLETED
    assert outcome.executor_id == "fake-1"
