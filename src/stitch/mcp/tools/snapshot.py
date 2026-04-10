"""Snapshot tools — capture, list, and diff operational state."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from stitch.mcp.services.snapshot_service import SnapshotService

if TYPE_CHECKING:
    from stitch.mcp.engine import StitchEngine


def register_snapshot_tools(mcp, engine: StitchEngine) -> None:
    svc = SnapshotService(engine)

    @mcp.tool()
    def stitch_snapshot_capture(label: str | None = None) -> str:
        """Capture OPNsense operational state (interfaces, firewall rules,
        routes, DHCP, system health) as timestamped JSON for later diffing."""
        return json.dumps(asyncio.run(svc.capture(label)).to_dict())

    @mcp.tool()
    def stitch_snapshot_list() -> str:
        """List available operational snapshots (most recent first, max 20)."""
        return json.dumps(svc.list_snapshots().to_dict())

    @mcp.tool()
    def stitch_snapshot_diff(before_file: str, after_file: str) -> str:
        """Compare two snapshots: added/removed/modified firewall rules,
        interfaces, routes, DHCP leases, etc."""
        return json.dumps(svc.diff(before_file, after_file).to_dict())
