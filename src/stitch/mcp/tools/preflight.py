"""Preflight verification tool — MCP wrapper over PreflightService."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from stitch.mcp.schemas import DetailLevel, ErrorCode, ToolResponse
from stitch.mcp.services.preflight_service import PreflightService
from stitch.opnsensecraft.collector import OpnsensecraftCollector

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from stitch.mcp.engine import StitchEngine


def register_preflight_tools(mcp: FastMCP, engine: StitchEngine) -> None:
    svc = PreflightService(engine)

    @mcp.tool()
    def stitch_preflight_run(
        topology_path: str | None = None,
        scope: str | None = None,
        detail: str = "standard",
    ) -> str:
        """Run preflight verification: collect live observations, merge, and verify against declared topology.

        Args:
            topology_path: Override topology file path (uses default if omitted).
            scope: Reserved for future filtering (unused).
            detail: Level of detail — summary, standard, or full.
        """  # noqa: E501
        try:
            detail_level = DetailLevel(detail)
        except ValueError:
            resp = ToolResponse.failure(
                ErrorCode.TOPOLOGY_INVALID,
                f"Invalid detail level: {detail!r}. Use summary, standard, or full.",
                summary="Invalid detail level.",
            )
            return json.dumps(resp.to_dict())

        # Auto-discover adapters from topology mcp_source fields
        try:
            topo = engine.get_topology(override_path=topology_path)
        except FileNotFoundError:
            resp = ToolResponse.failure(
                ErrorCode.TOPOLOGY_NOT_FOUND,
                "Topology not found",
                "Topology not found.",
            )
            return json.dumps(resp.to_dict())
        except Exception as e:
            resp = ToolResponse.failure(
                ErrorCode.TOPOLOGY_INVALID,
                str(e),
                f"Failed to load topology: {e}",
            )
            return json.dumps(resp.to_dict())

        adapters = []
        for dev_id, dev in topo.devices.items():
            d: dict = dev.model_dump() if hasattr(dev, "model_dump") else dict(dev)  # type: ignore[arg-type]
            source = d.get("mcp_source", "")
            if source == "opnsensecraft":
                adapters.append(
                    OpnsensecraftCollector(
                        dev_id,
                        device_name=d.get("name"),
                        management_ip=d.get("management_ip"),
                        gateway_url=engine.gateway_url,
                    )
                )

        resp = asyncio.run(
            svc.run(
                topology_path=topology_path,
                adapters=adapters,
                detail=detail_level,
            )
        )
        return json.dumps(resp.to_dict())
