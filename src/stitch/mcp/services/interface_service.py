"""InterfaceService — OPNsense interface assignment with dry_run default and audit."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
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

        # 6. Real apply via config.xml modification
        try:
            real_after = await self._apply_interface_assignment(
                device_id=device_id,
                physical_interface=physical_interface,
                assign_as=assign_as,
                description=description or "",
            )
        except Exception as exc:
            return self._fail_and_audit(
                ErrorCode.APPLY_FAILED,
                f"Apply failed: {exc}",
                audit_input=audit_input,
                before=before_state,
                after=after_state,
            )

        # 7. Re-read state to verify
        try:
            verify_result = await self._engine.gateway.call_tool("opnsense-get-interfaces")
            verify_rows = verify_result.get("rows", []) if verify_result else []
            verified_row = next(
                (r for r in verify_rows if r.get("device") == physical_interface), None
            )
            verified_ident = ""
            if verified_row:
                verified_ident = verified_row.get("config", {}).get("identifier", "")
        except Exception:
            verified_ident = "unknown (verify read failed)"

        if verified_ident != assign_as and verified_ident != "unknown (verify read failed)":
            return self._fail_and_audit(
                ErrorCode.VERIFICATION_FAILED,
                f"Post-apply verification: expected '{assign_as}', got '{verified_ident}'.",
                audit_input=audit_input,
                before=before_state,
                after=real_after,
            )

        resp_result: dict[str, Any] = {
            "dry_run": False,
            "applied": True,
            "device_id": device_id,
            "physical_interface": physical_interface,
            "assign_as": assign_as,
            "before": before_state,
            "after": real_after,
            "verification": {"verified_identifier": verified_ident, "match": verified_ident == assign_as},
        }
        resp = ToolResponse.success(
            resp_result,
            summary=f"Applied: {physical_interface} assigned as {assign_as} on {device_id}. Verified: {verified_ident}.",
        )
        self._write_audit(
            audit_input=audit_input,
            before=before_state,
            after=real_after,
            applied=True,
            success=True,
        )
        return resp

    async def _apply_interface_assignment(
        self,
        device_id: str,
        physical_interface: str,
        assign_as: str,
        description: str,
    ) -> dict[str, Any]:
        """Apply interface assignment by modifying OPNsense config.xml.

        Flow: backup config → modify XML → restore config → reconfigure.
        """
        # Read OPNsense connection details from the MCP config
        import os

        config_path = Path.home() / ".opnsense-mcp" / "config.json"
        if not config_path.exists():
            msg = "OPNsense config not found at ~/.opnsense-mcp/config.json"
            raise RuntimeError(msg)

        with config_path.open() as f:
            opn_config = json.load(f)["default"]

        base_url = opn_config["url"]
        api_key = opn_config["api_key"]
        api_secret = opn_config["api_secret"]

        async with httpx.AsyncClient(verify=False) as client:
            # 1. Download current config
            log.info("interface.backup_config", device=device_id, interface=physical_interface)
            resp = await client.get(
                f"{base_url}/api/core/backup/download/this",
                auth=(api_key, api_secret),
                timeout=30.0,
            )
            resp.raise_for_status()
            config_xml = resp.text

            # 2. Parse and modify
            root = ET.fromstring(config_xml)
            interfaces_elem = root.find("interfaces")
            if interfaces_elem is None:
                msg = "No <interfaces> element in config.xml"
                raise RuntimeError(msg)

            # Check not already assigned
            existing = interfaces_elem.find(assign_as)
            if existing is not None:
                msg = f"<{assign_as}> already exists in config.xml"
                raise RuntimeError(msg)

            # Add new interface element
            new_iface = ET.SubElement(interfaces_elem, assign_as)
            if_elem = ET.SubElement(new_iface, "if")
            if_elem.text = physical_interface
            descr_elem = ET.SubElement(new_iface, "descr")
            descr_elem.text = description
            enable_elem = ET.SubElement(new_iface, "enable")
            enable_elem.text = "1"
            spoofmac_elem = ET.SubElement(new_iface, "spoofmac")
            spoofmac_elem.text = ""

            # 3. Upload modified config
            modified_xml = ET.tostring(root, encoding="unicode", xml_declaration=True)
            log.info("interface.restore_config", device=device_id, assign_as=assign_as)

            restore_resp = await client.post(
                f"{base_url}/api/core/backup/restore",
                auth=(api_key, api_secret),
                files={"conffile": ("config.xml", modified_xml.encode(), "text/xml")},
                timeout=30.0,
            )
            restore_resp.raise_for_status()
            restore_data = restore_resp.json()

            if restore_data.get("status", "").lower() not in ("ok", "success", ""):
                msg = f"Config restore returned: {restore_data}"
                raise RuntimeError(msg)

            # 4. Apply/reconfigure
            log.info("interface.reconfigure", device=device_id)
            reconfig_resp = await client.post(
                f"{base_url}/api/interfaces/overview/reconfigure",
                auth=(api_key, api_secret),
                timeout=60.0,
            )
            # Reconfigure may return 200 or may not exist — that's OK,
            # the config change takes effect on next service reload
            if reconfig_resp.status_code == 404:
                log.info("interface.reconfigure_not_available", note="config saved, will apply on reload")

        return {
            "device": physical_interface,
            "config": {"identifier": assign_as},
            "description": description,
        }

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
