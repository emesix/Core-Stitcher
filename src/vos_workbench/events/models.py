from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4  # noqa: TC003

from pydantic import BaseModel, Field


class VosEvent(BaseModel):
    """CloudEvents-inspired event envelope for VOS-Workbench."""

    id: UUID = Field(default_factory=uuid4)
    type: str
    source: str
    time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    project_id: str
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    severity: Literal["debug", "info", "warning", "error"] = "info"
