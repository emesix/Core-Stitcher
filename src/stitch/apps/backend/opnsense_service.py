"""OPNsense backend service — calls MCP gateway, normalizes output, handles failures.

Sequential calls only (OPNsense rate limit). Per-tool timeout 5s, cache TTL 10s.
Broken categories return explicit degraded state without calling the gateway.
"""

from __future__ import annotations

import os
import time
from typing import Any

import structlog

from stitch.apps.backend.opnsense_models import (
    OpnsenseSummary,
    ServiceCard,
    ServiceStatus,
)
from stitch.contractkit.gateway import McpGatewayClient

log = structlog.get_logger()

_CACHE_TTL = 10.0  # seconds
_TOOL_TIMEOUT = 5.0  # per-tool timeout


def _default_gateway_url() -> str:
    return os.environ.get("MCP_GATEWAY_URL", "http://localhost:4444")


class OpnsenseService:
    """Calls OPNsense gateway tools and normalizes output into product-facing shapes."""

    def __init__(self, gateway_url: str | None = None) -> None:
        url = gateway_url or _default_gateway_url()
        self._gw = McpGatewayClient(url, max_retries=0)
        self._cache: dict[str, tuple[float, Any]] = {}

    def _cache_get(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        ts, data = entry
        if time.monotonic() - ts > _CACHE_TTL:
            del self._cache[key]
            return None
        return data

    def _cache_set(self, key: str, data: Any) -> None:
        self._cache[key] = (time.monotonic(), data)

    async def _call_tool(self, tool_name: str) -> Any | None:
        """Call a single gateway tool with timeout. Returns parsed result or None."""
        cached = self._cache_get(tool_name)
        if cached is not None:
            return cached
        try:
            result = await self._gw.call_tool(tool_name, timeout=_TOOL_TIMEOUT)
            if result is not None:
                self._cache_set(tool_name, result)
            return result
        except Exception:
            log.warning("opnsense.tool_failed", tool=tool_name, exc_info=True)
            return None

    # -- Individual endpoints --

    def _extract_rows(self, raw: Any) -> list[dict[str, Any]]:
        """Extract row list from gateway response (handles {rows:[...]} and plain lists)."""
        if raw is None:
            return []
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            if "rows" in raw:
                return raw["rows"]
            return list(raw.values())
        return []

    async def get_interfaces(self) -> list[dict[str, Any]]:
        raw = await self._call_tool("opnsense-get-interfaces")
        return self._extract_rows(raw)

    async def get_routes(self) -> list[dict[str, Any]]:
        raw = await self._call_tool("opnsense-get-system-routes")
        if isinstance(raw, dict) and "route" in raw:
            inner = raw["route"]
            if isinstance(inner, dict) and "route" in inner:
                result = inner["route"]
                return result if isinstance(result, list) else []
        return self._extract_rows(raw)

    async def get_aliases(self) -> list[dict[str, Any]]:
        raw = await self._call_tool("opnsense-get-firewall-aliases")
        return self._extract_rows(raw)

    async def get_nat(self) -> dict[str, Any]:
        raw = await self._call_tool("opnsense-nat-get-port-forward-info")
        if raw is None:
            return {"status": "error", "rules": []}
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, list):
            return {"rules": raw}
        return {"status": "unknown"}

    async def get_vlans(self) -> list[dict[str, Any]]:
        raw = await self._call_tool("opnsense-list-vlan-interfaces")
        return self._extract_rows(raw)

    async def get_bridges(self) -> list[dict[str, Any]]:
        raw = await self._call_tool("opnsense-list-bridge-interfaces")
        return self._extract_rows(raw)

    # -- Summary --

    async def get_summary(self) -> OpnsenseSummary:
        """Build full summary: 6 working tools + 8 known-broken categories."""
        cards: list[ServiceCard] = []

        # --- Working categories (sequential calls) ---

        # Interfaces
        interfaces = await self.get_interfaces()
        if interfaces:
            up_count = sum(
                1
                for iface in interfaces
                if isinstance(iface, dict) and iface.get("status", "").lower() == "up"
            )
            cards.append(
                ServiceCard(
                    name="interfaces",
                    status=ServiceStatus.WORKING,
                    headline=f"{len(interfaces)} interfaces, {up_count} up",
                    detail={"count": len(interfaces), "up": up_count},
                )
            )
        else:
            cards.append(
                ServiceCard(
                    name="interfaces",
                    status=ServiceStatus.ERROR,
                    headline="Failed to retrieve interfaces",
                    error="Gateway call returned no data",
                )
            )

        # Routes
        routes = await self.get_routes()
        if routes:
            cards.append(
                ServiceCard(
                    name="routes",
                    status=ServiceStatus.WORKING,
                    headline=f"{len(routes)} routes",
                    detail={"count": len(routes)},
                )
            )
        else:
            cards.append(
                ServiceCard(
                    name="routes",
                    status=ServiceStatus.ERROR,
                    headline="Failed to retrieve routes",
                    error="Gateway call returned no data",
                )
            )

        # Firewall aliases
        aliases = await self.get_aliases()
        if aliases:
            cards.append(
                ServiceCard(
                    name="firewall_aliases",
                    status=ServiceStatus.WORKING,
                    headline=f"{len(aliases)} aliases",
                    detail={"count": len(aliases)},
                )
            )
        else:
            cards.append(
                ServiceCard(
                    name="firewall_aliases",
                    status=ServiceStatus.ERROR,
                    headline="Failed to retrieve aliases",
                    error="Gateway call returned no data",
                )
            )

        # NAT
        nat = await self.get_nat()
        nat_rules = nat.get("rules", []) if isinstance(nat, dict) else []
        if nat and nat.get("status") != "error":
            cards.append(
                ServiceCard(
                    name="nat",
                    status=ServiceStatus.WORKING,
                    headline=f"{len(nat_rules)} port-forward rules"
                    if nat_rules
                    else "NAT configured",
                    detail=nat,
                )
            )
        else:
            cards.append(
                ServiceCard(
                    name="nat",
                    status=ServiceStatus.ERROR,
                    headline="Failed to retrieve NAT info",
                    error="Gateway call returned no data",
                )
            )

        # VLANs
        vlans = await self.get_vlans()
        if vlans:
            cards.append(
                ServiceCard(
                    name="vlans",
                    status=ServiceStatus.WORKING,
                    headline=f"{len(vlans)} VLANs",
                    detail={"count": len(vlans)},
                )
            )
        else:
            cards.append(
                ServiceCard(
                    name="vlans",
                    status=ServiceStatus.EMPTY,
                    headline="No VLANs configured",
                )
            )

        # Bridges
        bridges = await self.get_bridges()
        if bridges:
            cards.append(
                ServiceCard(
                    name="bridges",
                    status=ServiceStatus.WORKING,
                    headline=f"{len(bridges)} bridges",
                    detail={"count": len(bridges)},
                )
            )
        else:
            cards.append(
                ServiceCard(
                    name="bridges",
                    status=ServiceStatus.EMPTY,
                    headline="No bridges configured",
                )
            )

        # --- Known-broken categories (no gateway calls) ---

        cards.append(
            ServiceCard(
                name="system_status",
                status=ServiceStatus.ERROR,
                headline="System status unavailable",
                error="API endpoint not found on this OPNsense version",
            )
        )

        cards.append(
            ServiceCard(
                name="dhcp",
                status=ServiceStatus.ERROR,
                headline="DHCP data unavailable",
                error="Gateway tool error",
            )
        )

        cards.append(
            ServiceCard(
                name="dns",
                status=ServiceStatus.ERROR,
                headline="DNS data unavailable",
                error="Gateway tool error",
            )
        )

        cards.append(
            ServiceCard(
                name="vpn",
                status=ServiceStatus.UNSUPPORTED,
                headline="VPN not available",
                error="OpenVPN plugin not installed",
            )
        )

        cards.append(
            ServiceCard(
                name="certificates",
                status=ServiceStatus.ERROR,
                headline="Certificate data unavailable",
                error="API endpoint not found",
            )
        )

        cards.append(
            ServiceCard(
                name="users",
                status=ServiceStatus.ERROR,
                headline="User data unavailable",
                error="Gateway connection not configured",
            )
        )

        cards.append(
            ServiceCard(
                name="plugins",
                status=ServiceStatus.ERROR,
                headline="Plugin data unavailable",
                error="API endpoint not found",
            )
        )

        cards.append(
            ServiceCard(
                name="firewall_rules",
                status=ServiceStatus.EMPTY,
                headline="0 rules via API",
            )
        )

        return OpnsenseSummary(
            hostname="unknown",
            version="unknown",
            uptime=None,
            load=None,
            services=cards,
        )

    async def close(self) -> None:
        await self._gw.close()
