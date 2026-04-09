"""collectkit — Merge module that aggregates topology data from resource collectors.

Consumes the 'collect' capability from resource modules (switchcraft, opnsensecraft,
proxmoxcraft) and merges their output into a unified topology snapshot.
Provides the 'merge' capability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from stitch.collectkit.merger import merge_observations
from stitch_workbench.sdk import ModuleContext, ModuleManifest

if TYPE_CHECKING:
    from stitch.modelkit.observation import MergeConflict, Observation
    from stitch.modelkit.topology import TopologySnapshot


class CollectkitConfig(BaseModel):
    merge_strategy: str = "first_source"


class CollectkitModule:
    type_name = "resource.collectkit"
    version = "0.1.0"
    config_model = CollectkitConfig
    manifest = ModuleManifest(
        capabilities_provided=["merge"],
        capabilities_required=["collect"],
    )

    async def start(self, context: ModuleContext) -> None:
        self._context = context

    async def stop(self) -> None:
        pass

    async def health(self) -> dict[str, Any]:
        return {"status": "ok"}

    async def merge(
        self,
        observations: list[Observation],
    ) -> tuple[TopologySnapshot, list[MergeConflict]]:
        return merge_observations(observations)


__all__ = ["CollectkitConfig", "CollectkitModule", "merge_observations"]
