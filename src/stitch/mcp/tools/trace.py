"""Trace and impact preview tools — VLAN path tracing and change impact analysis."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from stitch.mcp.schemas import ErrorCode, ToolResponse
from stitch.modelkit.impact import ImpactRequest
from stitch.modelkit.trace import TraceRequest

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from stitch.mcp.engine import StitchEngine


def register_trace_tools(mcp: FastMCP, engine: StitchEngine) -> None:
    @mcp.tool()
    def stitch_trace_vlan(
        vlan: int,
        source: str | None = None,
        target: str | None = None,
    ) -> str:
        """Trace a VLAN path through the network topology."""
        try:
            explorer = engine.get_explorer()
            request = TraceRequest(vlan=vlan, source=source, target=target)
            result = explorer.trace(request)
            d = result.model_dump()
            hops = d.get("hops", [])
            status = d.get("status", "unknown")
            resp = ToolResponse.success(
                result=d,
                summary=f"VLAN {vlan}: {status} ({len(hops)} hops).",
                topology_path=engine.topology_path,
            )
        except FileNotFoundError:
            resp = ToolResponse.failure(
                ErrorCode.TOPOLOGY_NOT_FOUND,
                "Topology not found",
                "Topology not found.",
            )
        except Exception as e:
            resp = ToolResponse.failure(
                ErrorCode.TOPOLOGY_INVALID,
                str(e),
                f"Trace failed: {e}",
            )
        return json.dumps(resp.to_dict())

    @mcp.tool()
    def stitch_impact_preview(
        action: str,
        device: str,
        port: str | None = None,
        parameters: str | None = None,
    ) -> str:
        """Preview the impact of a proposed network change before applying it."""
        try:
            params: dict[str, Any] = {}
            if parameters is not None:
                try:
                    params = json.loads(parameters)
                except (json.JSONDecodeError, TypeError) as e:
                    resp = ToolResponse.failure(
                        ErrorCode.TOPOLOGY_INVALID,
                        f"Invalid parameters JSON: {e}",
                        "Parameters must be valid JSON.",
                    )
                    return json.dumps(resp.to_dict())

            explorer = engine.get_explorer()
            request = ImpactRequest(
                action=action,
                device=device,
                port=port,
                parameters=params,
            )
            result = explorer.impact(request)
            d = result.model_dump()
            risk = d.get("risk", "unknown")
            n_effects = len(d.get("impact", []))
            resp = ToolResponse.success(
                result=d,
                summary=f"Impact: {risk} risk, {n_effects} effect(s).",
                topology_path=engine.topology_path,
            )
        except FileNotFoundError:
            resp = ToolResponse.failure(
                ErrorCode.TOPOLOGY_NOT_FOUND,
                "Topology not found",
                "Topology not found.",
            )
        except Exception as e:
            resp = ToolResponse.failure(
                ErrorCode.TOPOLOGY_INVALID,
                str(e),
                f"Impact preview failed: {e}",
            )
        return json.dumps(resp.to_dict())
