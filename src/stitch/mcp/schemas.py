"""Response envelope, error codes, and shared types for MCP tools."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class DetailLevel(StrEnum):
    SUMMARY = "summary"
    STANDARD = "standard"
    FULL = "full"


class ErrorCode(StrEnum):
    TOPOLOGY_NOT_FOUND = "TOPOLOGY_NOT_FOUND"
    TOPOLOGY_INVALID = "TOPOLOGY_INVALID"
    DEVICE_NOT_FOUND = "DEVICE_NOT_FOUND"
    DEVICE_AMBIGUOUS = "DEVICE_AMBIGUOUS"
    GATEWAY_UNAVAILABLE = "GATEWAY_UNAVAILABLE"
    GATEWAY_TOOL_ERROR = "GATEWAY_TOOL_ERROR"
    GATEWAY_TIMEOUT = "GATEWAY_TIMEOUT"
    INTERFACE_NOT_FOUND = "INTERFACE_NOT_FOUND"
    INTERFACE_ALREADY_ASSIGNED = "INTERFACE_ALREADY_ASSIGNED"
    APPLY_FAILED = "APPLY_FAILED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"


TOOL_VERSION = "1.0"


class ToolResponse:
    def __init__(
        self,
        ok: bool,
        summary: str,
        result: dict[str, Any] | None = None,
        error: dict[str, str] | None = None,
        topology_path: str | None = None,
    ):
        self.ok = ok
        self.summary = summary
        self.result = result
        self.error = error
        self.topology_path = topology_path

    @classmethod
    def success(cls, result: Any, summary: str, topology_path: str | None = None) -> ToolResponse:
        return cls(ok=True, summary=summary, result=result, topology_path=topology_path)

    @classmethod
    def failure(
        cls,
        code: str | ErrorCode,
        message: str,
        summary: str,
        topology_path: str | None = None,
    ) -> ToolResponse:
        return cls(
            ok=False,
            summary=summary,
            error={"code": str(code), "message": message},
            topology_path=topology_path,
        )

    def to_dict(self) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "tool_version": TOOL_VERSION,
            "generated_at": datetime.now(UTC).isoformat(),
        }
        if self.topology_path:
            meta["topology_path"] = self.topology_path
        d: dict[str, Any] = {"ok": self.ok, "summary": self.summary, "meta": meta}
        if self.ok:
            d["result"] = self.result
        else:
            d["error"] = self.error
        return d
