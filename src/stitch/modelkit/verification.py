from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from vos.modelkit.enums import CheckCategory, CheckSeverity, ObservationSource

__all__ = [
    "CheckResult",
    "LinkVerification",
    "VerificationReport",
]


def _utcnow() -> datetime:
    return datetime.now(UTC)


class CheckResult(BaseModel):
    check: str
    port: str
    expected: Any
    observed: Any
    source: ObservationSource
    flag: str
    message: str | None = None
    category: CheckCategory | None = None
    severity: CheckSeverity = CheckSeverity.INFO


class LinkVerification(BaseModel):
    link: str
    link_type: str
    status: str
    highest_severity: CheckSeverity = CheckSeverity.INFO
    checks: list[CheckResult] = Field(default_factory=list)


class VerificationReport(BaseModel):
    timestamp: datetime = Field(default_factory=_utcnow)
    results: list[LinkVerification] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
