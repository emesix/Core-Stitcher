"""MCP Gateway client — shared transport for all collectors.

Handles authentication and the Streamable HTTP transport used by the
MCP gateway at localhost:4444. Reads the auth token from the
MCP_GATEWAY_AUTH environment variable.

Features:
- Persistent httpx.AsyncClient for connection pooling / reuse.
- Configurable retry with exponential backoff (transport errors + 5xx only).
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx
import structlog

log = structlog.get_logger()

MCP_GATEWAY_URL = "http://localhost:4444"
MCP_GATEWAY_AUTH_ENV = "MCP_GATEWAY_AUTH"

_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_SECONDS = (1.0, 2.0, 4.0)


def _is_retryable(exc: Exception) -> bool:
    """Return True for errors worth retrying (transport / 5xx)."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    # TimeoutException is a subclass of HTTPError, check it first
    return isinstance(exc, httpx.TimeoutException | httpx.ConnectError | httpx.ReadError)


class McpGatewayClient:
    """Calls MCP tools via the gateway's Streamable HTTP endpoint."""

    def __init__(
        self,
        gateway_url: str = MCP_GATEWAY_URL,
        *,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        backoff_seconds: tuple[float, ...] = _DEFAULT_BACKOFF_SECONDS,
    ) -> None:
        self._gateway_url = gateway_url.rstrip("/")
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._client: httpx.AsyncClient | None = None

    def _get_client(self, timeout: float) -> httpx.AsyncClient:
        """Return the persistent client, creating it lazily on first use."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=timeout)
        return self._client

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        token = os.environ.get(MCP_GATEWAY_AUTH_ENV)
        if token:
            headers["Authorization"] = token
        return headers

    async def close(self) -> None:
        """Close the persistent HTTP client and release connections."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        *,
        timeout: float = 60.0,
    ) -> Any:
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

        last_exc: Exception | None = None

        for attempt in range(1 + self._max_retries):
            try:
                client = self._get_client(timeout)
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
                    log.warning(
                        "mcp.empty_content", tool=tool_name, raw_result=result
                    )
                    return None

                text = content[0].get("text")
                if not text:
                    log.warning("mcp.no_text", tool=tool_name, content=content)
                    return None

                return json.loads(text)

            except httpx.HTTPStatusError as exc:
                if not _is_retryable(exc):
                    # 4xx — not retryable, bail immediately
                    log.warning(
                        "mcp.http_error",
                        tool=tool_name,
                        status=exc.response.status_code,
                        body=exc.response.text[:500],
                    )
                    return None
                last_exc = exc
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as exc:
                last_exc = exc
            except httpx.HTTPError as exc:
                # Non-retryable transport error (e.g. decode, redirect loop)
                log.warning(
                    "mcp.transport_error",
                    tool=tool_name,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                return None
            except json.JSONDecodeError as exc:
                log.warning(
                    "mcp.json_error",
                    tool=tool_name,
                    error=str(exc),
                )
                return None

            # Retryable failure — log and back off
            delay = (
                self._backoff_seconds[attempt]
                if attempt < len(self._backoff_seconds)
                else self._backoff_seconds[-1]
            )
            log.warning(
                "mcp.retry",
                tool=tool_name,
                attempt=attempt + 1,
                max_retries=self._max_retries,
                delay_s=delay,
                error_type=type(last_exc).__name__,
                error=str(last_exc),
            )

            if attempt < self._max_retries:
                await asyncio.sleep(delay)

        # All retries exhausted
        log.warning(
            "mcp.retries_exhausted",
            tool=tool_name,
            attempts=1 + self._max_retries,
            last_error=str(last_exc),
        )
        return None
