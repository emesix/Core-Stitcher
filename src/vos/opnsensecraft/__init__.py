"""opnsensecraft — Resource module for collecting topology data from OPNsense firewalls.

Connects to OPNsense via the MCP gateway and retrieves interface, VLAN, and
bridge data. Provides the 'collect' capability consumed by collectkit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from vos.opnsensecraft.collector import OpnsensecraftCollector
from vos_workbench.sdk import ModuleContext, ModuleManifest

if TYPE_CHECKING:
    from vos.modelkit.observation import Observation


class OpnsensecraftConfig(BaseModel):
    device_slug: str
    device_name: str = ""
    management_ip: str | None = None
    gateway_url: str = "http://localhost:4444"


class OpnsensecraftModule:
    type_name = "resource.opnsensecraft"
    version = "0.1.0"
    config_model = OpnsensecraftConfig
    manifest = ModuleManifest(
        capabilities_provided=["collect"],
        capabilities_required=[],
    )

    def __init__(self) -> None:
        self._collector: OpnsensecraftCollector | None = None
        self._context: ModuleContext | None = None

    async def start(self, context: ModuleContext) -> None:
        self._context = context
        config: OpnsensecraftConfig = context.config
        self._collector = OpnsensecraftCollector(
            device_slug=config.device_slug,
            device_name=config.device_name or None,
            management_ip=config.management_ip,
            gateway_url=config.gateway_url,
        )

    async def stop(self) -> None:
        self._collector = None

    async def health(self) -> dict[str, Any]:
        if self._collector is None:
            return {"status": "error", "message": "Module not started"}
        return await self._collector.check_health()

    async def collect(self) -> list[Observation]:
        if self._collector is None:
            return []
        return await self._collector.collect()


__all__ = ["OpnsensecraftCollector", "OpnsensecraftConfig", "OpnsensecraftModule"]
