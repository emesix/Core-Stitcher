"""switchcraft — Resource module for collecting topology data from network switches.

Connects to switches via the switchcraft MCP gateway and retrieves interface,
VLAN, and neighbour data. Provides the 'collect' capability consumed by collectkit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from vos.modelkit.enums import PortType
from vos.switchcraft.collector import SwitchcraftCollector
from vos_workbench.sdk import ModuleContext, ModuleManifest

if TYPE_CHECKING:
    from vos.modelkit.observation import Observation

_PORT_TYPE_MAP: dict[str, PortType] = {
    "sfp+": PortType.SFP_PLUS,
    "ethernet": PortType.ETHERNET,
    "bridge": PortType.BRIDGE,
    "vlan": PortType.VLAN,
    "virtual": PortType.VIRTUAL,
}


class SwitchcraftConfig(BaseModel):
    mcp_device_id: str
    device_slug: str
    device_name: str = ""
    gateway_url: str = "http://localhost:4444"
    management_ip: str | None = None
    port_type: str = "sfp+"
    tags: list[str] = Field(default_factory=list)


class SwitchcraftModule:
    type_name = "resource.switchcraft"
    version = "0.1.0"
    config_model = SwitchcraftConfig
    manifest = ModuleManifest(
        capabilities_provided=["collect"],
        capabilities_required=[],
    )

    def __init__(self) -> None:
        self._collector: SwitchcraftCollector | None = None
        self._context: ModuleContext | None = None

    async def start(self, context: ModuleContext) -> None:
        self._context = context
        config: SwitchcraftConfig = context.config
        self._collector = SwitchcraftCollector(
            device_slug=config.device_slug,
            mcp_device_id=config.mcp_device_id,
            device_name=config.device_name or None,
            gateway_url=config.gateway_url,
            port_type=_PORT_TYPE_MAP.get(config.port_type, PortType.SFP_PLUS),
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


__all__ = ["SwitchcraftCollector", "SwitchcraftConfig", "SwitchcraftModule"]
