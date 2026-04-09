"""Stream model -- live event subscriptions."""
from __future__ import annotations

from datetime import datetime  # noqa: TC003 (Pydantic needs runtime access)
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from stitch.core.queries import Filter  # noqa: TC001 (Pydantic needs runtime access)


class StreamTopic(StrEnum):
    RUN_PROGRESS = "run.progress"
    RUN_LOG = "run.log"
    TASK_STATUS = "task.status"
    REVIEW_VERDICT = "review.verdict"
    MODULE_HEALTH = "module.health"
    TOPOLOGY_CHANGE = "topology.change"
    SYSTEM_EVENT = "system.event"


class StreamSubscription(BaseModel):
    topic: StreamTopic
    target: str | None = None
    filters: list[Filter] = []
    last_event_id: str | None = None


class StreamEvent(BaseModel):
    event_id: str
    sequence: int
    topic: StreamTopic
    resource: str
    payload: dict[str, Any]
    timestamp: datetime
    correlation_id: str | None = None
