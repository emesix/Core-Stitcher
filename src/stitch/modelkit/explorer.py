from __future__ import annotations

from pydantic import BaseModel, Field

from vos.modelkit.enums import LinkType, VlanMode

__all__ = [
    "DanglingPort",
    "Neighbor",
    "TopologyDiagnostics",
    "VlanPortEntry",
]


class Neighbor(BaseModel, frozen=True):
    device: str
    local_port: str
    remote_port: str
    link_id: str
    link_type: LinkType


class DanglingPort(BaseModel, frozen=True):
    device: str
    port: str
    reason: str


class VlanPortEntry(BaseModel, frozen=True):
    device: str
    port: str
    mode: VlanMode


class TopologyDiagnostics(BaseModel):
    dangling_ports: list[DanglingPort] = Field(default_factory=list)
    orphan_devices: list[str] = Field(default_factory=list)
    missing_endpoints: list[str] = Field(default_factory=list)
    total_devices: int = 0
    total_ports: int = 0
    total_links: int = 0
