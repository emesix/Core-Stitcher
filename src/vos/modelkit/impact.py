from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "ImpactRequest",
    "ImpactEffect",
    "ImpactResult",
]


class ImpactRequest(BaseModel, frozen=True):
    action: str
    device: str
    port: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class ImpactEffect(BaseModel):
    device: str
    port: str | None = None
    effect: str
    severity: str


class ImpactResult(BaseModel):
    proposed_change: ImpactRequest
    impact: list[ImpactEffect] = Field(default_factory=list)
    risk: str
    safe_to_apply: bool
    highest_severity: str = "info"
    highlights: list[str] = Field(default_factory=list)
