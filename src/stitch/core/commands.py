"""Command model -- state-changing actions."""
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class CommandSource(StrEnum):
    CLI = "cli"
    TUI = "tui"
    WEB = "web"
    LITE = "lite"
    DESKTOP = "desktop"
    API = "api"
    SCRIPT = "script"
    INTERNAL = "internal"


class ExecutionMode(StrEnum):
    SYNC = "sync"
    ASYNC = "async"


class InteractionClass(StrEnum):
    NONE = "none"
    CONFIRM = "confirm"
    FORM = "form"
    WIZARD = "wizard"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Command(BaseModel):
    action: str
    target: str | None = None
    params: dict[str, Any] = {}
    source: CommandSource = CommandSource.CLI
    correlation_id: str = ""
    idempotency_key: str | None = None
