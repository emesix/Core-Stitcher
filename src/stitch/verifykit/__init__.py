"""verifykit — Core module for topology verification and contract checking.

Validates a topology snapshot against contractkit contracts, checking that
VLAN assignments, routing, and device connections satisfy declared constraints.
Provides the 'verify' capability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from vos.verifykit.engine import verify_topology
from vos_workbench.sdk import ModuleContext, ModuleManifest

if TYPE_CHECKING:
    from vos.modelkit.topology import TopologySnapshot
    from vos.modelkit.verification import VerificationReport


class VerifykitConfig(BaseModel):
    pass


class VerifykitModule:
    type_name = "core.verifykit"
    version = "0.1.0"
    config_model = VerifykitConfig
    manifest = ModuleManifest(
        capabilities_provided=["verify"],
        capabilities_required=[],
    )

    async def start(self, context: ModuleContext) -> None:
        self._context = context

    async def stop(self) -> None:
        pass

    async def health(self) -> dict[str, Any]:
        return {"status": "ok"}

    async def verify(
        self,
        declared: TopologySnapshot,
        observed: TopologySnapshot,
    ) -> VerificationReport:
        return verify_topology(declared, observed)


__all__ = ["VerifykitConfig", "VerifykitModule", "verify_topology"]
