"""Executor protocol — the contract for task execution backends."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from stitch.agentcore.taskkit.models import TaskOutcome, TaskRecord


class ExecutorHealth(BaseModel, frozen=True):
    status: str  # "ok", "degraded", "error"
    message: str | None = None
    latency_ms: float | None = None


class ExecutorCapability(BaseModel, frozen=True):
    """Declares what an executor can handle."""

    domains: list[str] = Field(default_factory=list)
    max_concurrent: int = 1
    supports_streaming: bool = False
    tags: list[str] = Field(default_factory=list)


class _HealthStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    ERROR = "error"


@runtime_checkable
class ExecutorProtocol(Protocol):
    @property
    def executor_id(self) -> str: ...

    @property
    def capability(self) -> ExecutorCapability: ...

    async def execute(self, task: TaskRecord) -> TaskOutcome: ...

    async def health(self) -> ExecutorHealth: ...
