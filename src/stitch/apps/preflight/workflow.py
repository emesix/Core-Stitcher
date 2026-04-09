"""PreflightWorkflow — implements PreflightWorkflowProtocol.

Orchestrates: load declared → collect from adapters → merge → verify → report.
Almost zero domain logic — just wiring.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from stitch.collectkit.merger import merge_observations
from stitch.storekit import load_topology
from stitch.tracekit.impact import preview_impact
from stitch.tracekit.tracer import trace_vlan_path
from stitch.verifykit.engine import verify_topology

if TYPE_CHECKING:
    from stitch.contractkit.collector import CollectorProtocol
    from stitch.modelkit.impact import ImpactRequest, ImpactResult
    from stitch.modelkit.topology import TopologySnapshot
    from stitch.modelkit.trace import TraceRequest, TraceResult
    from stitch.modelkit.verification import VerificationReport


class PreflightWorkflow:
    """Composes the preflight verification pipeline.

    Accepts dependencies directly for testability. In production, these would
    be resolved via CapabilityResolver from the spine SDK.
    """

    def __init__(
        self,
        topology_path: str | Path,
        collectors: list[CollectorProtocol],
    ) -> None:
        self._topology_path = Path(topology_path)
        self._collectors = collectors

    async def run_verification(self) -> VerificationReport:
        declared = load_topology(self._topology_path)
        observations = await self._collect_all()
        observed, _conflicts = merge_observations(observations)
        return verify_topology(declared, observed)

    async def run_trace(self, request: TraceRequest) -> TraceResult:
        declared = load_topology(self._topology_path)
        return trace_vlan_path(declared, request)

    async def run_impact_preview(self, request: ImpactRequest) -> ImpactResult:
        declared = load_topology(self._topology_path)
        return preview_impact(declared, request)

    async def _collect_all(self) -> list:
        tasks = [collector.collect() for collector in self._collectors]
        results = await asyncio.gather(*tasks)
        # Flatten list of lists
        all_obs = []
        for obs_list in results:
            all_obs.extend(obs_list)
        return all_obs

    @property
    def declared_topology(self) -> TopologySnapshot:
        return load_topology(self._topology_path)
