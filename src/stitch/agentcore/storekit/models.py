"""Persistence models — RunRecord, step audit trail, policy types."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from vos.agentcore.plannerkit.models import PlanRecord, WorkRequest  # noqa: TC001
from vos.agentcore.reviewkit.models import ReviewResult  # noqa: TC001
from vos.agentcore.taskkit.models import TaskOutcome  # noqa: TC001

# --- Orchestration policy types (here to avoid circular imports) ---


class StepKind(StrEnum):
    DOMAIN_CALL = "domain_call"
    AI_SUMMARY = "ai_summary"
    AI_REVIEW = "ai_review"
    CORRECTION = "correction"


class StepStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SelectionReason(StrEnum):
    DOMAIN_MATCH = "domain_match"
    GENERAL_FALLBACK = "general_fallback"
    ONLY_AVAILABLE = "only_available"
    NO_EXECUTOR = "no_executor"
    BUDGET_EXHAUSTED = "budget_exhausted"
    POLICY_DISALLOWED = "policy_disallowed"
    ESCALATED = "escalated"


class ExecutorSelection(BaseModel, frozen=True):
    """Why a specific executor was chosen for a step."""

    executor_id: str | None = None
    reason: SelectionReason
    candidates_considered: int = 0
    domain_matches: int = 0


class StepRecord(BaseModel):
    """One step in an orchestrated run with full audit trail."""

    step_id: UUID = Field(default_factory=uuid4)
    kind: StepKind
    status: StepStatus = StepStatus.COMPLETED
    description: str = ""
    iteration: int = 0
    selection: ExecutorSelection | None = None
    result: Any = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


# --- Run types ---


class RunStatus(StrEnum):
    CREATED = "created"
    PLANNED = "planned"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TaskExecution(BaseModel):
    """One task's execution result within a run."""

    task_id: UUID
    description: str
    domain: str | None = None
    executor_id: str | None = None
    outcome: TaskOutcome | None = None


class RunRecord(BaseModel):
    """A complete pipeline run: request → plan → executions → reviews."""

    run_id: UUID = Field(default_factory=uuid4)
    status: RunStatus = RunStatus.CREATED
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    request: WorkRequest | None = None
    plan: PlanRecord | None = None
    executions: list[TaskExecution] = Field(default_factory=list)
    reviews: list[ReviewResult] = Field(default_factory=list)
    steps: list[StepRecord] = Field(default_factory=list)
    summary: str | None = None
