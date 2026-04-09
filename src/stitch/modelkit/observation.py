from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from stitch.modelkit.enums import ObservationSource

__all__ = [
    "Observation",
    "Mismatch",
    "MergeConflict",
]


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Observation(BaseModel):
    device: str
    port: str | None = None
    field: str
    value: Any
    source: ObservationSource
    adapter: str | None = None
    timestamp: datetime = Field(default_factory=_utcnow)


class Mismatch(BaseModel):
    device: str
    port: str | None = None
    field: str
    expected: Any
    observed: Any
    source: ObservationSource
    severity: str = "error"
    message: str | None = None


class MergeConflict(BaseModel):
    device: str
    port: str | None = None
    field: str
    sources: list[str] = Field(default_factory=list)
    values: list[Any] = Field(default_factory=list)
    resolution: str | None = None
