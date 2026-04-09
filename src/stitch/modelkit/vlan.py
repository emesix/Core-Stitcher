from __future__ import annotations

from pydantic import BaseModel

__all__ = [
    "VlanMetadata",
]


class VlanMetadata(BaseModel, frozen=True):
    name: str
    color: str | None = None
    subnet: str | None = None
    gateway: str | None = None
