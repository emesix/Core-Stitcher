"""proxmoxcraft — Resource module for collecting topology data from Proxmox hypervisors.

Connects to Proxmox via the MCP gateway and retrieves bridge, NIC, and
VLAN data. Provides the 'collect' capability consumed by collectkit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from vos.proxmoxcraft.collector import ProxmoxcraftCollector
from vos_workbench.sdk import ModuleContext, ModuleManifest

if TYPE_CHECKING:
    from vos.modelkit.observation import Observation


class ProxmoxcraftConfig(BaseModel):
    device_slug: str
    node_name: str
    device_name: str = ""
    management_ip: str | None = None
    gateway_url: str = "http://localhost:4444"


class ProxmoxcraftModule:
    type_name = "resource.proxmoxcraft"
    version = "0.1.0"
    config_model = ProxmoxcraftConfig
    manifest = ModuleManifest(
        capabilities_provided=["collect"],
        capabilities_required=[],
    )

    def __init__(self) -> None:
        self._collector: ProxmoxcraftCollector | None = None
        self._context: ModuleContext | None = None

    async def start(self, context: ModuleContext) -> None:
        self._context = context
        config: ProxmoxcraftConfig = context.config
        self._collector = ProxmoxcraftCollector(
            device_slug=config.device_slug,
            node_name=config.node_name,
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


__all__ = ["ProxmoxcraftCollector", "ProxmoxcraftConfig", "ProxmoxcraftModule"]
