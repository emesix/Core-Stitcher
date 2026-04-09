from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WorkbenchError(BaseModel):
    error_id: UUID = Field(default_factory=uuid4)
    source_module: UUID | None = None
    severity: Literal["warning", "error", "fatal"]
    category: Literal[
        "config",
        "dependency",
        "execution",
        "budget",
        "policy",
        "provider",
        "internal",
    ]
    retryable: bool
    message: str
    user_summary: str
    details: dict[str, Any] = {}
    detail_truncated: bool = False
    artifact_ref: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
