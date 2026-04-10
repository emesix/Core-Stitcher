"""Stitch MCP server — entry point."""

from __future__ import annotations

import os

from fastmcp import FastMCP

from stitch.mcp.engine import StitchEngine
from stitch.mcp.tools.topology import register_topology_tools

mcp = FastMCP(
    "stitch",
    instructions=(
        "Core-Stitcher domain engine: topology verification,"
        " VLAN tracing, impact analysis, device inspection."
    ),
)

engine = StitchEngine(
    topology_path=os.environ.get("STITCH_TOPOLOGY", "topologies/lab.json"),
    gateway_url=os.environ.get("MCP_GATEWAY_URL", "http://localhost:4444"),
)

register_topology_tools(mcp, engine)


def main() -> None:
    mcp.run(transport="stdio")
