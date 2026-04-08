from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from vos.modelkit.device import Device
from vos.modelkit.link import Link
from vos.modelkit.vlan import VlanMetadata

__all__ = [
    "TopologyMeta",
    "TopologySnapshot",
]


class TopologyMeta(BaseModel, frozen=True):
    version: str
    name: str
    updated: datetime | None = None
    updated_by: str | None = None


class TopologySnapshot(BaseModel):
    meta: TopologyMeta
    devices: dict[str, Device] = Field(default_factory=dict)
    links: list[Link] = Field(default_factory=list)
    vlans: dict[str, VlanMetadata] = Field(default_factory=dict)
