"""OpnsensecraftCollector — CollectorProtocol implementation.

Calls opnsense MCP get-interfaces tool via the MCP gateway and normalizes
the response into Observation objects. Single API call provides everything:
physical ports, VLANs, bridges, and IP addresses.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx

from vos.opnsensecraft.normalizer import normalize_device_identity, normalize_interfaces

if TYPE_CHECKING:
    from vos.modelkit.observation import Observation

MCP_GATEWAY_URL = "http://localhost:4444"


class OpnsensecraftCollector:
    """Collects topology observations from OPNsense via MCP."""

    def __init__(
        self,
        device_slug: str,
        *,
        device_name: str | None = None,
        management_ip: str | None = None,
        gateway_url: str = MCP_GATEWAY_URL,
    ) -> None:
        self._device_slug = device_slug
        self._device_name = device_name
        self._management_ip = management_ip
        self._gateway_url = gateway_url

    async def collect(self) -> list[Observation]:
        observations: list[Observation] = []

        observations.extend(
            normalize_device_identity(
                self._device_slug,
                device_name=self._device_name,
                management_ip=self._management_ip,
            )
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            ifaces = await self._call_tool(client, "get-interfaces")

        if ifaces is not None:
            observations.extend(normalize_interfaces(self._device_slug, ifaces))

        return observations

    async def check_health(self) -> dict[str, Any]:
        """Check OPNsense reachability via MCP gateway."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                result = await self._call_tool(client, "get-interfaces")
        except Exception:
            return {
                "status": "error",
                "device": self._device_slug,
                "message": "MCP gateway unreachable",
            }

        if result is None:
            return {
                "status": "error",
                "device": self._device_slug,
                "message": "No response from MCP tool",
            }

        row_count = result.get("rowCount", 0)
        return {
            "status": "ok",
            "device": self._device_slug,
            "interfaces": row_count,
        }

    async def _call_tool(
        self,
        client: httpx.AsyncClient,
        tool_suffix: str,
    ) -> dict[str, Any] | None:
        """Call an opnsense MCP tool via the gateway's JSON-RPC endpoint."""
        tool_name = f"opnsense-{tool_suffix}"
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": {},
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
