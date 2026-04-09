"""tracekit — Core module for tracing paths and previewing topology changes.

Traverses topology snapshots to trace network paths between endpoints and
previews the effect of proposed configuration changes before they are applied.
Provides the 'trace' and 'preview' capabilities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from stitch.tracekit.impact import preview_impact
from stitch.tracekit.tracer import trace_vlan_path
from stitch_workbench.sdk import ModuleContext, ModuleManifest

if TYPE_CHECKING:
    from stitch.modelkit.impact import ImpactRequest, ImpactResult
    from stitch.modelkit.topology import TopologySnapshot
    from stitch.modelkit.trace import TraceRequest, TraceResult


class TracekitConfig(BaseModel):
    pass


class TracekitModule:
    type_name = "core.tracekit"
    version = "0.1.0"
    config_model = TracekitConfig
    manifest = ModuleManifest(
        capabilities_provided=["trace", "preview"],
        capabilities_required=[],
    )

    def __init__(self) -> None:
        self._context: ModuleContext | None = None

    async def start(self, context: ModuleContext) -> None:
        self._context = context

    async def stop(self) -> None:
        pass

    async def health(self) -> dict[str, Any]:
        return {"status": "ok"}

    async def trace(self, snapshot: TopologySnapshot, request: TraceRequest) -> TraceResult:
        return trace_vlan_path(snapshot, request)

    async def preview(
        self,
        snapshot: TopologySnapshot,
        request: ImpactRequest,
    ) -> ImpactResult:
        return preview_impact(snapshot, request)


__all__ = ["TracekitConfig", "TracekitModule", "preview_impact", "trace_vlan_path"]
