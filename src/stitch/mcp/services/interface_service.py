"""InterfaceService — OPNsense interface assignment with dry_run default and audit."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from stitch.mcp.schemas import ErrorCode, ToolResponse

if TYPE_CHECKING:
    from stitch.mcp.engine import StitchEngine

log = structlog.get_logger()

AUDIT_PATH = Path.home() / ".stitch" / "audit.jsonl"


class InterfaceService:
    def __init__(self, engine: StitchEngine) -> None:
        self._engine = engine

    async def assign(
        self,
        device_id: str,
        physical_interface: str,
        assign_as: str,
        description: str | None = None,
        *,
        dry_run: bool = True,
    ) -> ToolResponse:
        audit_input: dict[str, Any] = {
            "device_id": device_id,
            "physical_interface": physical_interface,
            "assign_as": assign_as,
            "description": description,
            "dry_run": dry_run,
        }

        # 1. Validate device_id exists in topology
        try:
            topo = self._engine.get_topology()
        except FileNotFoundError:
            return self._fail_and_audit(
                ErrorCode.DEVICE_NOT_FOUND,
                "Topology file not found.",
                audit_input=audit_input,
            )

        if device_id not in topo.devices:
            return self._fail_and_audit(
                ErrorCode.DEVICE_NOT_FOUND,
                f"Device '{device_id}' not found in topology.",
                audit_input=audit_input,
            )

        # 2. Call opnsense-get-interfaces via gateway
        try:
            result = await self._engine.gateway.call_tool(
                "opnsense-get-interfaces",
                {"device_id": device_id},
            )
        except Exception as exc:
            return self._fail_and_audit(
                ErrorCode.GATEWAY_UNAVAILABLE,
                f"Gateway call failed: {exc}",
                audit_input=audit_input,
            )

        if result is None:
            return self._fail_and_audit(
                ErrorCode.GATEWAY_UNAVAILABLE,
                "Gateway returned no data (RPC error or empty response).",
                audit_input=audit_input,
            )

        # 3. Find the target physical_interface in rows
        rows: list[dict[str, Any]] = result.get("rows", [])
        target_row: dict[str, Any] | None = None
        for row in rows:
            if row.get("device") == physical_interface:
                target_row = row
                break

        if target_row is None:
            return self._fail_and_audit(
                ErrorCode.INTERFACE_NOT_FOUND,
                f"Interface '{physical_interface}' not found on device '{device_id}'.",
                audit_input=audit_input,
            )

        # 4. Check if already assigned
        config = target_row.get("config", {})
        identifier = config.get("identifier", "")
        if identifier:
            return self._fail_and_audit(
                ErrorCode.INTERFACE_ALREADY_ASSIGNED,
                f"Interface '{physical_interface}' is already assigned as '{identifier}'.",
                audit_input=audit_input,
            )

        before_state = {
            "device": physical_interface,
            "config": config,
            "description": target_row.get("description", ""),
        }

        after_state = {
            "device": physical_interface,
            "config": {"identifier": assign_as},
            "description": description or target_row.get("description", ""),
        }

        # 5. If dry_run: return projected state
        if dry_run:
            resp_result: dict[str, Any] = {
                "dry_run": True,
                "applied": False,
                "device_id": device_id,
                "physical_interface": physical_interface,
                "assign_as": assign_as,
                "before": before_state,
                "after": after_state,
            }
            resp = ToolResponse.success(
                resp_result,
                summary=(
                    f"Dry run: would assign {physical_interface} as {assign_as} on {device_id}."
                ),
            )
            self._write_audit(
                audit_input=audit_input,
                before=before_state,
                after=after_state,
                applied=False,
                success=True,
            )
            return resp

        # 6. Real apply not yet implemented
        resp = self._fail_and_audit(
            ErrorCode.APPLY_FAILED,
            "Real apply not yet implemented in v1. Use dry_run=True.",
            audit_input=audit_input,
            before=before_state,
            after=after_state,
        )
        return resp

    def _fail_and_audit(
        self,
        code: ErrorCode,
        message: str,
        *,
        audit_input: dict[str, Any],
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> ToolResponse:
        resp = ToolResponse.failure(code, message, summary=message)
        self._write_audit(
            audit_input=audit_input,
            before=before,
            after=after,
            applied=False,
            success=False,
        )
        return resp

    def _write_audit(
        self,
        *,
        audit_input: dict[str, Any],
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        applied: bool,
        success: bool,
    ) -> None:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "tool": "stitch_interface_assign",
            "input": audit_input,
            "before": before,
            "after": after,
            "applied": applied,
            "success": success,
        }
        try:
            AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
            with AUDIT_PATH.open("a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as exc:
            log.warning("audit.write_failed", error=str(exc))
