from __future__ import annotations

from pydantic import BaseModel

from vos.modelkit.enums import LinkType

__all__ = [
    "LinkEndpoint",
    "Link",
]


class LinkEndpoint(BaseModel, frozen=True):
    device: str
    port: str


class Link(BaseModel):
    id: str
    type: LinkType
    endpoints: tuple[LinkEndpoint, LinkEndpoint]
    media: str | None = None
    cable_color: str | None = None
    notes: str | None = None
