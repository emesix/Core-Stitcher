from __future__ import annotations

from pydantic import BaseModel, Field

from stitch.modelkit.enums import DeviceType
from stitch.modelkit.port import Port

__all__ = [
    "Position",
    "Device",
]


class Position(BaseModel, frozen=True):
    x: float
    y: float


class Device(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    name: str
    type: DeviceType
    model: str | None = None
    management_ip: str | None = None
    mcp_source: str | None = None
    position: Position | None = None
    ports: dict[str, Port] = Field(default_factory=dict)
    children: list[str] = Field(default_factory=list)
