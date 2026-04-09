"""Auth and session types."""
from __future__ import annotations

from datetime import datetime  # noqa: TC003 (Pydantic needs runtime access)
from enum import StrEnum

from pydantic import BaseModel

from stitch.core.commands import CommandSource  # noqa: TC001 (Pydantic needs runtime access)


class Capability(StrEnum):
    TOPOLOGY_READ = "topology.read"
    PREFLIGHT_RUN = "preflight.run"
    TRACE_RUN = "trace.run"
    IMPACT_RUN = "impact.run"
    RUNS_MANAGE = "runs.manage"
    RUNS_REVIEW = "runs.review"
    CHANGES_APPROVE = "changes.approve"
    LOGS_VIEW = "logs.view"
    ADMIN = "admin"


class Session(BaseModel):
    session_id: str
    user: str
    capabilities: set[str]
    scopes: dict[str, list[str]] | None = None
    client: CommandSource
    created_at: datetime
    expires_at: datetime | None = None
