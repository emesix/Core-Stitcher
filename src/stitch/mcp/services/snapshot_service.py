"""Snapshot service — capture and diff OPNsense operational state."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from stitch.mcp.schemas import ErrorCode, ToolResponse

log = structlog.get_logger()

SNAPSHOT_DIR = Path("snapshots")

# What we capture in each snapshot
CAPTURE_TOOLS = [
    ("interfaces", "opnsense-get-interfaces", {}),
    ("firewall_rules", "opnsense-firewall-get-rules", {}),
    ("system_routes", "opnsense-get-system-routes", {}),
    ("dhcp_leases", "opnsense-dhcp-get-leases", {}),
    ("dhcp_static_mappings", "opnsense-dhcp-list-static-mappings", {}),
    ("system_status", "opnsense-get-system-status", {}),
    ("system_health", "opnsense-get-system-health", {}),
]


class SnapshotService:
    def __init__(self, engine: Any) -> None:
        self._engine = engine

    async def capture(self, label: str | None = None) -> ToolResponse:
        """Capture current OPNsense state as a timestamped snapshot."""
        timestamp = datetime.now(UTC)
        ts_str = timestamp.strftime("%Y%m%dT%H%M%SZ")
        label_str = f"-{label}" if label else ""
        filename = f"{ts_str}{label_str}.json"

        snapshot: dict[str, Any] = {
            "timestamp": timestamp.isoformat(),
            "label": label or "",
            "sections": {},
            "errors": [],
        }

        for section_name, tool_name, args in CAPTURE_TOOLS:
            try:
                result = await self._engine.gateway.call_tool(tool_name, args)
                snapshot["sections"][section_name] = result
                log.info("snapshot.captured", section=section_name)
            except Exception as exc:
                snapshot["errors"].append({"section": section_name, "error": str(exc)})
                log.warning("snapshot.section_failed", section=section_name, error=str(exc))

        # Save to snapshots/
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        path = SNAPSHOT_DIR / filename
        with path.open("w") as f:
            json.dump(snapshot, f, indent=2, default=str)

        captured = list(snapshot["sections"].keys())
        failed = [e["section"] for e in snapshot["errors"]]

        return ToolResponse.success(
            result={
                "file": str(path),
                "timestamp": timestamp.isoformat(),
                "label": label or "",
                "captured": captured,
                "failed": failed,
                "section_count": len(captured),
            },
            summary=(
                f"Snapshot saved: {filename}"
                f" ({len(captured)} sections captured, {len(failed)} failed)."
            ),
        )

    def list_snapshots(self) -> ToolResponse:
        """List available snapshots."""
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(SNAPSHOT_DIR.glob("*.json"), reverse=True)

        items = []
        for f in files[:20]:  # last 20
            try:
                with f.open() as fh:
                    data = json.load(fh)
                items.append(
                    {
                        "file": f.name,
                        "timestamp": data.get("timestamp", ""),
                        "label": data.get("label", ""),
                        "sections": list(data.get("sections", {}).keys()),
                        "error_count": len(data.get("errors", [])),
                    }
                )
            except Exception:
                items.append(
                    {
                        "file": f.name,
                        "timestamp": "",
                        "label": "corrupt",
                        "sections": [],
                        "error_count": -1,
                    }
                )

        return ToolResponse.success(
            result={"snapshots": items, "total": len(files)},
            summary=f"{len(files)} snapshots available. Showing latest {len(items)}.",
        )

    def diff(self, before_file: str, after_file: str) -> ToolResponse:
        """Diff two snapshots and report changes."""
        before_path = SNAPSHOT_DIR / before_file
        after_path = SNAPSHOT_DIR / after_file

        if not before_path.exists():
            return ToolResponse.failure(
                ErrorCode.TOPOLOGY_NOT_FOUND,
                f"Snapshot not found: {before_file}",
                f"Before snapshot '{before_file}' not found.",
            )
        if not after_path.exists():
            return ToolResponse.failure(
                ErrorCode.TOPOLOGY_NOT_FOUND,
                f"Snapshot not found: {after_file}",
                f"After snapshot '{after_file}' not found.",
            )

        with before_path.open() as f:
            before = json.load(f)
        with after_path.open() as f:
            after = json.load(f)

        changes: dict[str, Any] = {}
        all_sections = set(before.get("sections", {}).keys()) | set(
            after.get("sections", {}).keys()
        )

        for section in sorted(all_sections):
            b_data = before.get("sections", {}).get(section)
            a_data = after.get("sections", {}).get(section)

            if b_data is None and a_data is not None:
                changes[section] = {"change": "added", "detail": "Section newly captured."}
            elif b_data is not None and a_data is None:
                changes[section] = {"change": "removed", "detail": "Section no longer captured."}
            elif json.dumps(b_data, sort_keys=True, default=str) != json.dumps(
                a_data, sort_keys=True, default=str
            ):
                # Section changed — compute a meaningful diff per section type
                changes[section] = self._diff_section(section, b_data, a_data)
            # else: unchanged, skip

        changed_count = len(changes)
        unchanged_count = len(all_sections) - changed_count

        return ToolResponse.success(
            result={
                "before": {"file": before_file, "timestamp": before.get("timestamp", "")},
                "after": {"file": after_file, "timestamp": after.get("timestamp", "")},
                "changes": changes,
                "changed_sections": changed_count,
                "unchanged_sections": unchanged_count,
            },
            summary=(
                f"Diff: {changed_count} sections changed,"
                f" {unchanged_count} unchanged"
                f" between {before_file} and {after_file}."
            ),
        )

    def _diff_section(self, section: str, before: Any, after: Any) -> dict[str, Any]:
        """Compute a human-useful diff for a specific section type."""
        if section == "firewall_rules":
            return self._diff_list_by_key(before, after, key="uuid", label="rules")
        if section == "dhcp_leases":
            return self._diff_list_by_key(before, after, key="address", label="leases")
        if section == "dhcp_static_mappings":
            return self._diff_list_by_key(before, after, key="mac", label="mappings")
        if section == "interfaces":
            return self._diff_list_by_key(before, after, key="device", label="interfaces")
        if section == "system_routes":
            return self._diff_list_by_key(before, after, key="destination", label="routes")
        # Generic: just report changed
        return {
            "change": "modified",
            "detail": "Content differs (no structured diff for this section).",
        }

    def _diff_list_by_key(self, before: Any, after: Any, key: str, label: str) -> dict[str, Any]:
        """Diff two lists of dicts by a key field."""
        b_rows = self._extract_rows(before)
        a_rows = self._extract_rows(after)

        b_by_key = {r.get(key, str(i)): r for i, r in enumerate(b_rows)}
        a_by_key = {r.get(key, str(i)): r for i, r in enumerate(a_rows)}

        added = [k for k in a_by_key if k not in b_by_key]
        removed = [k for k in b_by_key if k not in a_by_key]
        modified = []
        for k in b_by_key:
            if k in a_by_key and json.dumps(
                b_by_key[k], sort_keys=True, default=str
            ) != json.dumps(a_by_key[k], sort_keys=True, default=str):
                modified.append(k)

        return {
            "change": "modified",
            f"added_{label}": added,
            f"removed_{label}": removed,
            f"modified_{label}": modified,
            "counts": {"added": len(added), "removed": len(removed), "modified": len(modified)},
        }

    def _extract_rows(self, data: Any) -> list[dict]:
        """Extract row list from various OPNsense response formats."""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if "rows" in data:
                return data["rows"]
            if "data" in data:
                return data["data"]
        return []
