"""OPNsense capability models — sweep results and service summaries.

Used by the automated sweep script and the backend normalization layer.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — Pydantic needs this at runtime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class ToolClassification(StrEnum):
    SAFE_READ = "safe_read"
    SENSITIVE_READ = "sensitive_read"
    SAFE_ACTION = "safe_action"
    DANGEROUS = "dangerous"


class ProbeStatus(StrEnum):
    WORKS = "works"
    EMPTY = "empty"
    AUTH_ERROR = "auth_error"
    NOT_FOUND = "not_found"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class ToolProbeResult(BaseModel):
    tool: str
    category: str
    classification: ToolClassification
    status: ProbeStatus
    latency_ms: float | None = None
    item_count: int | None = None
    error_code: str | None = None
    error_message: str | None = None


class CapabilitySweepResult(BaseModel):
    timestamp: datetime
    target: str
    results: list[ToolProbeResult]
    summary: dict[str, int]


class ServiceStatus(StrEnum):
    WORKING = "working"
    EMPTY = "configured_but_empty"
    UNSUPPORTED = "unsupported"
    ERROR = "error"
    TIMEOUT = "timed_out"


class ServiceCard(BaseModel):
    name: str
    status: ServiceStatus
    headline: str
    detail: dict[str, Any] = {}
    error: str | None = None


class OpnsenseSummary(BaseModel):
    hostname: str
    version: str
    uptime: str | None = None
    load: str | None = None
    services: list[ServiceCard]
