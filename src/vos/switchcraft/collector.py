"""SwitchcraftCollector — CollectorProtocol implementation.

Calls switchcraft MCP tools (get-ports, get-vlans, device-status) via the
MCP gateway and normalizes responses into Observation objects.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx

from vos.modelkit.enums import PortType
from vos.switchcraft.normalizer import normalize_ports, normalize_status, normalize_vlans

if TYPE_CHECKING:
    from vos.modelkit.observation import Observation

MCP_GATEWAY_URL = "http://localhost:4444"


class SwitchcraftCollector:
    """Collects topology observations from a single switch via switchcraft MCP."""

    def __init__(
        self,
        device_slug: str,
        mcp_device_id: str,
        *,
        device_name: str | None = None,
        device_type: str = "switch",
        port_type: PortType = PortType.SFP_PLUS,
        gateway_url: str = MCP_GATEWAY_URL,
    ) -> None:
        self._device_slug = device_slug
        self._mcp_device_id = mcp_device_id
        self._device_name = device_name
        self._device_type = device_type
        self._port_type = port_type
        self._gateway_url = gateway_url

    async def collect(self) -> list[Observation]:
        observations: list[Observation] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            status_resp = await self._call_tool(client, "device-status")
            ports_resp = await self._call_tool(client, "get-ports")
            vlans_resp = await self._call_tool(client, "get-vlans")

        if status_resp is not None:
            observations.extend(
                normalize_status(
                    self._device_slug,
                    status_resp,
                    device_type=self._device_type,
                    device_name=self._device_name,
                )
            )

        if ports_resp is not None:
            observations.extend(
                normalize_ports(self._device_slug, ports_resp, port_type=self._port_type)
            )

        if vlans_resp is not None:
            observations.extend(normalize_vlans(self._device_slug, vlans_resp))

        return observations

    async def check_health(self) -> dict[str, Any]:
        """Check device reachability via the MCP gateway."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                status = await self._call_tool(client, "device-status")
        except Exception:
            return {
                "status": "error",
                "device_id": self._mcp_device_id,
                "message": "MCP gateway unreachable",
            }

        if status is None:
            return {
                "status": "error",
                "device_id": self._mcp_device_id,
                "message": "No response from MCP tool",
            }

        reachable = status.get("reachable", False)
        result: dict[str, Any] = {
            "status": "ok" if reachable else "degraded",
            "device_id": self._mcp_device_id,
            "reachable": reachable,
        }
        if status.get("uptime"):
            result["uptime"] = status["uptime"]
        if status.get("firmware"):
            result["firmware"] = status["firmware"]
        if status.get("error"):
            result["message"] = status["error"]
        return result

    async def _call_tool(
        self,
        client: httpx.AsyncClient,
        tool_suffix: str,
    ) -> dict[str, Any] | None:
        """Call a switchcraft MCP tool via the gateway's JSON-RPC endpoint."""
        tool_name = f"switchcraft-{tool_suffix}"
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": {"device_id": self._mcp_device_id},
            },
        }

        try:
            resp = await client.post(f"{self._gateway_url}/mcp", json=payload)
            resp.raise_for_status()
            result = resp.json()

            # MCP response: {"result": {"content": [{"text": "...json..."}]}}
            content = result.get("result", {}).get("content", [])
            if content and content[0].get("text"):
                return json.loads(content[0]["text"])
        except httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError:
            return None

        return None
