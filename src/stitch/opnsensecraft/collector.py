"""OpnsensecraftCollector — CollectorProtocol implementation.

Calls opnsense MCP get-interfaces tool via the MCP gateway and normalizes
the response into Observation objects. Single API call provides everything:
physical ports, VLANs, bridges, and IP addresses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from stitch.contractkit.gateway import McpGatewayClient
from stitch.opnsensecraft.normalizer import normalize_device_identity, normalize_interfaces

if TYPE_CHECKING:
    from stitch.modelkit.observation import Observation


class OpnsensecraftCollector:
    """Collects topology observations from OPNsense via MCP."""

    def __init__(
        self,
        device_slug: str,
        *,
        device_name: str | None = None,
        management_ip: str | None = None,
        gateway_url: str | None = None,
    ) -> None:
        self._device_slug = device_slug
        self._device_name = device_name
        self._management_ip = management_ip
        self._gw = McpGatewayClient(gateway_url) if gateway_url else McpGatewayClient()

    async def collect(self) -> list[Observation]:
        observations: list[Observation] = []

        observations.extend(
            normalize_device_identity(
                self._device_slug,
                device_name=self._device_name,
                management_ip=self._management_ip,
            )
        )

        ifaces = await self._gw.call_tool("opnsense-get-interfaces")

        if ifaces is not None:
            observations.extend(normalize_interfaces(self._device_slug, ifaces))

        return observations

    async def check_health(self) -> dict[str, Any]:
        """Check OPNsense reachability via MCP gateway."""
        try:
            result = await self._gw.call_tool("opnsense-get-interfaces")
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
