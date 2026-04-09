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
import structlog

log = structlog.get_logger()

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
        args = arguments or {}
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args,
            },
        }
        has_auth = MCP_GATEWAY_AUTH_ENV in os.environ

        log.debug("mcp.call", tool=tool_name, args=args, has_auth=has_auth)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{self._gateway_url}/mcp/",
                    json=payload,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                result = resp.json()

                # Check for JSON-RPC error envelope
                if "error" in result:
                    rpc_error = result["error"]
                    log.warning(
                        "mcp.rpc_error",
                        tool=tool_name,
                        code=rpc_error.get("code"),
                        message=rpc_error.get("message"),
                    )
                    return None

                content = result.get("result", {}).get("content", [])
                if not content:
                    log.warning("mcp.empty_content", tool=tool_name, raw_result=result)
                    return None

                text = content[0].get("text")
                if not text:
                    log.warning("mcp.no_text", tool=tool_name, content=content)
                    return None

                return json.loads(text)

        except httpx.TimeoutException as exc:
            log.warning(
                "mcp.timeout",
                tool=tool_name,
                timeout_s=timeout,
                error=str(exc),
            )
        except httpx.HTTPStatusError as exc:
            log.warning(
                "mcp.http_error",
                tool=tool_name,
                status=exc.response.status_code,
                body=exc.response.text[:500],
            )
        except httpx.HTTPError as exc:
            log.warning(
                "mcp.transport_error",
                tool=tool_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )
        except json.JSONDecodeError as exc:
            log.warning(
                "mcp.json_error",
                tool=tool_name,
                error=str(exc),
            )

        return None
