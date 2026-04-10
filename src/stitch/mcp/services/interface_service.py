"""InterfaceService — OPNsense interface assignment with dry_run default and audit."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
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
            "verification": {
                "verified_identifier": verified_ident,
                "match": verified_ident == assign_as,
            },
        }
        resp = ToolResponse.success(
            resp_result,
            summary=(
                f"Applied: {physical_interface} assigned as {assign_as}"
                f" on {device_id}. Verified: {verified_ident}."
            ),
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
        """Apply interface assignment via SSH + config.xml modification.

        Flow: SSH read config → modify XML → SSH write config → reconfigure.
        Option A from the design: SSH + configctl (native OPNsense path).
        """
        import asyncio
        import os
        import subprocess

        # Read OPNsense SSH credentials from env or config
        opn_host = os.environ.get("OPNSENSE_SSH_HOST", "172.16.0.1")
        opn_user = os.environ.get("OPNSENSE_SSH_USER", "root")
        opn_pass = os.environ.get("OPNSENSE_SSH_PASS", "")
        # Guard against unexpanded template vars (e.g. "${OPNSENSE_SSH_PASS}")
        if not opn_pass or opn_pass.startswith("$"):
            # Fall back to config file
            config_path = Path.home() / ".stitch" / "ssh.json"
            if config_path.exists():
                with config_path.open() as f:
                    ssh_cfg = json.load(f)
                opn_pass = ssh_cfg.get("opnsense_pass", "")
            if not opn_pass:
                msg = "No SSH password: set OPNSENSE_SSH_PASS env or create ~/.stitch/ssh.json"
                raise RuntimeError(msg)

        def _ssh(cmd: str, *, timeout: int = 30) -> str:
            result = subprocess.run(
                [
                    "sshpass",
                    "-p",
                    opn_pass,
                    "ssh",
                    "-o",
                    "StrictHostKeyChecking=accept-new",
                    f"{opn_user}@{opn_host}",
                    cmd,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0:
                msg = f"SSH command failed: {result.stderr.strip()}"
                raise RuntimeError(msg)
            return result.stdout

        # 1. Backup current config via SSH
        log.info("interface.ssh_backup", device=device_id, interface=physical_interface)
        config_xml = await asyncio.to_thread(_ssh, "cat /conf/config.xml")

        # 2. Parse and modify
        root = ET.fromstring(config_xml)
        interfaces_elem = root.find("interfaces")
        if interfaces_elem is None:
            msg = "No <interfaces> element in config.xml"
            raise RuntimeError(msg)

        # Check not already assigned in config
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

        modified_xml = ET.tostring(root, encoding="unicode", xml_declaration=True)

        # 3. Write modified config via SSH (with backup)
        log.info("interface.ssh_write_config", device=device_id, assign_as=assign_as)
        # Backup first
        await asyncio.to_thread(_ssh, "cp /conf/config.xml /conf/config.xml.bak")
        # Write via stdin to avoid quoting issues
        write_result = subprocess.run(
            [
                "sshpass",
                "-p",
                opn_pass,
                "ssh",
                "-o",
                "StrictHostKeyChecking=accept-new",
                f"{opn_user}@{opn_host}",
                "cat > /conf/config.xml",
            ],
            input=modified_xml,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if write_result.returncode != 0:
            msg = f"Config write failed: {write_result.stderr.strip()}"
            raise RuntimeError(msg)

        # 4. Reload config via configctl
        log.info("interface.ssh_reconfigure", device=device_id)
        try:
            await asyncio.to_thread(_ssh, "configctl interface reconfigure", timeout=60)
        except Exception as exc:
            log.warning(
                "interface.reconfigure_warning",
                error=str(exc),
                note="config saved, may need manual reload",
            )

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
