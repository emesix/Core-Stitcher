"""ProxmoxcraftCollector — CollectorProtocol implementation.

Calls proxmox MCP tools (node-status, list-bridges) via the MCP gateway
and normalizes responses into Observation objects. Focuses on node-level
network topology: physical NICs, bridges, and their members.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx

from vos.proxmoxcraft.normalizer import normalize_network, normalize_node_identity

if TYPE_CHECKING:
    from vos.modelkit.observation import Observation

MCP_GATEWAY_URL = "http://localhost:4444"


class ProxmoxcraftCollector:
    """Collects topology observations from a single Proxmox node via MCP."""

    def __init__(
        self,
        device_slug: str,
        node_name: str,
        *,
        device_name: str | None = None,
        management_ip: str | None = None,
        gateway_url: str = MCP_GATEWAY_URL,
    ) -> None:
        self._device_slug = device_slug
        self._node_name = node_name
        self._device_name = device_name
        self._management_ip = management_ip
        self._gateway_url = gateway_url

    async def collect(self) -> list[Observation]:
        observations: list[Observation] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            status = await self._call_tool(client, "node-status", {"node": self._node_name})
            bridges = await self._call_tool(client, "list-bridges", {"node": self._node_name})

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
            # list-bridges returns only bridges; for full network picture
            # we use bridges as the authoritative source since it includes
            # bridge_ports (member NICs)
            observations.extend(normalize_network(self._device_slug, bridges))

        return observations

    async def check_health(self) -> dict[str, Any]:
        """Check Proxmox node reachability via MCP gateway."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                status = await self._call_tool(
                    client,
                    "node-status",
                    {"node": self._node_name},
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

    async def _call_tool(
        self,
        client: httpx.AsyncClient,
        tool_suffix: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any | None:
        """Call a proxmox MCP tool via the gateway's JSON-RPC endpoint."""
        tool_name = f"proxmox-{tool_suffix}"
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {},
            },
        }

        try:
            resp = await client.post(f"{self._gateway_url}/mcp", json=payload)
            resp.raise_for_status()
            result = resp.json()

            content = result.get("result", {}).get("content", [])
            if content and content[0].get("text"):
                return json.loads(content[0]["text"])
        except httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError:
            return None

        return None
