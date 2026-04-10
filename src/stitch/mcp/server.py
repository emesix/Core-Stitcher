"""Stitch MCP server — entry point."""

from __future__ import annotations

from fastmcp import FastMCP

mcp = FastMCP(
    "stitch",
    instructions=(
        "Core-Stitcher domain engine: topology verification,"
        " VLAN tracing, impact analysis, device inspection."
    ),
)


def main() -> None:
    mcp.run(transport="stdio")
