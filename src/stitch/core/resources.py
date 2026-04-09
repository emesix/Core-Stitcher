"""Resource identity -- URIs, parsing, and the Resource summary type."""
from __future__ import annotations

import re

from pydantic import BaseModel

from stitch.core.lifecycle import LifecycleState  # noqa: TC001 (Pydantic needs runtime access)

_URI_RE = re.compile(
    r"^stitch:/"
    r"(?P<type>[a-z_]+)/(?P<id>[^/]+)"
    r"(?:/(?P<sub_type>[a-z_]+)/(?P<sub_id>[^/]+))?"
    r"(?:/(?P<extra>.+))?$"
)


class ResourceURI(BaseModel):
    resource_type: str
    resource_id: str
    sub_resource: str | None = None
    sub_id: str | None = None
    extra_path: str | None = None

    def __str__(self) -> str:
        s = f"stitch:/{self.resource_type}/{self.resource_id}"
        if self.sub_resource and self.sub_id:
            s += f"/{self.sub_resource}/{self.sub_id}"
        if self.extra_path:
            s += f"/{self.extra_path}"
        return s


class Resource(BaseModel):
    """Navigable summary of any addressable entity."""

    uri: str
    type: str
    display_name: str
    summary: str
    status: LifecycleState | None = None
    parent: str | None = None
    children_hint: int | None = None


def parse_uri(uri: str) -> ResourceURI:
    m = _URI_RE.match(uri)
    if not m:
        msg = f"Invalid stitch URI: {uri}"
        raise ValueError(msg)
    return ResourceURI(
        resource_type=m.group("type"),
        resource_id=m.group("id"),
        sub_resource=m.group("sub_type"),
        sub_id=m.group("sub_id"),
        extra_path=m.group("extra"),
    )
