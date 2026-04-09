"""Review data types — findings, verdicts, and review results."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ReviewVerdict(StrEnum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    REJECT = "reject"


class ReviewFinding(BaseModel, frozen=True):
    """A single issue or observation found during review."""

    description: str
    severity: Severity = Severity.INFO
    task_id: UUID | None = None
    category: str | None = None
    suggestion: str | None = None


class ReviewRequest(BaseModel):
    """Input to a review — what should be reviewed and against what criteria."""

    review_id: UUID = Field(default_factory=uuid4)
    plan_id: UUID | None = None
    task_id: UUID | None = None
    content: Any = None
    criteria: list[str] = Field(default_factory=list)


class ReviewResult(BaseModel):
    """Output of a review — findings and a verdict."""

    review_id: UUID = Field(default_factory=uuid4)
    request_id: UUID | None = None
    verdict: ReviewVerdict = ReviewVerdict.APPROVE
    findings: list[ReviewFinding] = Field(default_factory=list)
    summary: str = ""

    @property
    def has_errors(self) -> bool:
        return any(f.severity in (Severity.ERROR, Severity.CRITICAL) for f in self.findings)

    @property
    def has_warnings(self) -> bool:
        return any(f.severity == Severity.WARNING for f in self.findings)

    def findings_by_severity(self, severity: Severity) -> list[ReviewFinding]:
        return [f for f in self.findings if f.severity == severity]
