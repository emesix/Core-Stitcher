from __future__ import annotations

from pydantic import BaseModel, Field

from vos.modelkit.enums import PortType, VlanMode

__all__ = [
    "VlanMembership",
    "ExpectedNeighbor",
    "Port",
]


class VlanMembership(BaseModel, frozen=True):
    mode: VlanMode
    native: int | None = None
    tagged: list[int] = Field(default_factory=list)
    access_vlan: int | None = None


class ExpectedNeighbor(BaseModel, frozen=True):
    device: str
    port: str
    mac: str | None = None


class Port(BaseModel):
    type: PortType
    device_name: str | None = None
    speed: str | None = None
    mac: str | None = None
    description: str | None = None
    vlans: VlanMembership | None = None
    expected_neighbor: ExpectedNeighbor | None = None
