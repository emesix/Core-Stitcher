from __future__ import annotations

from pydantic import BaseModel, Field

from vos.modelkit.enums import ObservationSource

__all__ = [
    "TraceRequest",
    "TraceHop",
    "BreakPoint",
    "TraceResult",
]


class TraceRequest(BaseModel, frozen=True):
    vlan: int
    source: str | None = None
    target: str | None = None


class TraceHop(BaseModel):
    device: str | None = None
    port: str | None = None
    link: str | None = None
    status: str
    source: ObservationSource
    reason: str | None = None


class BreakPoint(BaseModel, frozen=True):
    device: str
    port: str
    reason: str
    likely_causes: list[str] = Field(default_factory=list)


class TraceResult(BaseModel):
    vlan: int
    source: str | None = None
    target: str | None = None
    status: str
    hops: list[TraceHop] = Field(default_factory=list)
    first_break: BreakPoint | None = None
