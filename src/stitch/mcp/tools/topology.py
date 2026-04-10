"""Topology read tools — thin MCP wrappers over TopologyService."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from stitch.mcp.schemas import DetailLevel
from stitch.mcp.services.topology_service import TopologyService

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from stitch.mcp.engine import StitchEngine


def register_topology_tools(mcp: FastMCP, engine: StitchEngine) -> None:
    svc = TopologyService(engine)

    @mcp.tool()
    def stitch_topology_summary(topology_path: str | None = None) -> str:
        """Get topology summary: device/link/VLAN counts and device types."""
        return json.dumps(svc.summary(topology_path).to_dict())

    @mcp.tool()
    def stitch_devices(
        topology_path: str | None = None,
        detail: str = "standard",
    ) -> str:
        """List all devices. detail: summary|standard|full."""
        return json.dumps(svc.devices(topology_path, detail=DetailLevel(detail)).to_dict())

    @mcp.tool()
    def stitch_device_detail(device_id: str, topology_path: str | None = None) -> str:
        """Get full detail for a single device including all ports."""
        return json.dumps(svc.device_detail(device_id, topology_path).to_dict())

    @mcp.tool()
    def stitch_device_neighbors(device_id: str, topology_path: str | None = None) -> str:
        """Get all neighbors of a device (devices connected via links)."""
        return json.dumps(svc.device_neighbors(device_id, topology_path).to_dict())

    @mcp.tool()
    def stitch_diagnostics(topology_path: str | None = None) -> str:
        """Run topology diagnostics: find dangling ports, orphan devices, and missing endpoints."""
        return json.dumps(svc.diagnostics(topology_path).to_dict())
