"""SwitchcraftCollector — CollectorProtocol implementation.

Calls switchcraft MCP tools (get-ports, get-vlans, device-status) via the
MCP gateway and normalizes responses into Observation objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from vos.contractkit.gateway import McpGatewayClient
from vos.modelkit.enums import PortType
from vos.switchcraft.normalizer import normalize_ports, normalize_status, normalize_vlans

if TYPE_CHECKING:
    from vos.modelkit.observation import Observation


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
        gateway_url: str | None = None,
    ) -> None:
        self._device_slug = device_slug
        self._mcp_device_id = mcp_device_id
        self._device_name = device_name
        self._device_type = device_type
        self._port_type = port_type
        self._gw = McpGatewayClient(gateway_url) if gateway_url else McpGatewayClient()

    async def collect(self) -> list[Observation]:
        observations: list[Observation] = []

        status_resp = await self._gw.call_tool(
            "switchcraft-device-status", {"device_id": self._mcp_device_id}
        )
        ports_resp = await self._gw.call_tool(
            "switchcraft-get-ports", {"device_id": self._mcp_device_id}
        )
        vlans_resp = await self._gw.call_tool(
            "switchcraft-get-vlans", {"device_id": self._mcp_device_id}
        )

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
            status = await self._gw.call_tool(
                "switchcraft-device-status", {"device_id": self._mcp_device_id}
            )
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
