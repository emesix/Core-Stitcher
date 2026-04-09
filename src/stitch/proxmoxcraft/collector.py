"""ProxmoxcraftCollector — CollectorProtocol implementation.

Calls proxmox MCP tools (node-status, list-bridges) via the MCP gateway
and normalizes responses into Observation objects. Focuses on node-level
network topology: physical NICs, bridges, and their members.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from stitch.contractkit.gateway import McpGatewayClient
from stitch.proxmoxcraft.normalizer import normalize_network, normalize_node_identity

if TYPE_CHECKING:
    from stitch.modelkit.observation import Observation


class ProxmoxcraftCollector:
    """Collects topology observations from a single Proxmox node via MCP."""

    def __init__(
        self,
        device_slug: str,
        node_name: str,
        *,
        device_name: str | None = None,
        management_ip: str | None = None,
        gateway_url: str | None = None,
    ) -> None:
        self._device_slug = device_slug
        self._node_name = node_name
        self._device_name = device_name
        self._management_ip = management_ip
        self._gw = McpGatewayClient(gateway_url) if gateway_url else McpGatewayClient()

    async def collect(self) -> list[Observation]:
        observations: list[Observation] = []

        status = await self._gw.call_tool(
            "proxmox-proxmox-node-status", {"node": self._node_name}
        )
        bridges = await self._gw.call_tool(
            "proxmox-proxmox-list-bridges", {"node": self._node_name}
        )

        if status is not None:
            observations.extend(
                normalize_node_identity(
                    self._device_slug,
                    status,
                    device_name=self._device_name,
                    management_ip=self._management_ip,
                )
            )

        if bridges is not None:
            observations.extend(normalize_network(self._device_slug, bridges))

        return observations

    async def check_health(self) -> dict[str, Any]:
        """Check Proxmox node reachability via MCP gateway."""
        try:
            status = await self._gw.call_tool(
                "proxmox-proxmox-node-status", {"node": self._node_name}
            )
        except Exception:
            return {
                "status": "error",
                "device": self._device_slug,
                "message": "MCP gateway unreachable",
            }

        if status is None:
            return {
                "status": "error",
                "device": self._device_slug,
                "message": "No response from MCP tool",
            }

        return {
            "status": "ok",
            "device": self._device_slug,
            "node": self._node_name,
            "uptime": status.get("uptime"),
            "pve_version": status.get("pveversion"),
        }
