"""Task data types — the unit of work in agent orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TaskOutcome(BaseModel, frozen=True):
    """Result of a completed or failed task."""

    status: TaskStatus
    result: Any = None
    error: str | None = None
    executor_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class TaskRecord(BaseModel):
    """A single unit of work to be routed to an executor."""

    id: UUID = Field(default_factory=uuid4)
    parent_id: UUID | None = None
    description: str
    domain: str | None = None
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=_utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
    outcome: TaskOutcome | None = None

    def is_terminal(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
