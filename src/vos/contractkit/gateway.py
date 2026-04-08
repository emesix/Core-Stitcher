"""MCP Gateway client — shared transport for all collectors.

Handles authentication and the Streamable HTTP transport used by the
MCP gateway at localhost:4444. Reads the auth token from the
MCP_GATEWAY_AUTH environment variable.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

MCP_GATEWAY_URL = "http://localhost:4444"
MCP_GATEWAY_AUTH_ENV = "MCP_GATEWAY_AUTH"


class McpGatewayClient:
    """Calls MCP tools via the gateway's Streamable HTTP endpoint."""

    def __init__(self, gateway_url: str = MCP_GATEWAY_URL) -> None:
        self._gateway_url = gateway_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        token = os.environ.get(MCP_GATEWAY_AUTH_ENV)
        if token:
            headers["Authorization"] = token
        return headers

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        *,
        timeout: float = 60.0,
    ) -> dict[str, Any] | None:
        """Call an MCP tool and return the parsed JSON result, or None on failure."""
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
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{self._gateway_url}/mcp/",
                    json=payload,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                result = resp.json()

                content = result.get("result", {}).get("content", [])
                if content and content[0].get("text"):
                    return json.loads(content[0]["text"])
        except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError):
            return None

        return None
