"""Stitch API client — async HTTP with auth."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx

from stitch.core.errors import (
    StitchAPIError,
    StitchError,
    StitchTransportError,
    TransportError,
)
from stitch.core.queries import QueryResult
from stitch.sdk.auth import resolve_auth
from stitch.sdk.endpoints import resolve_endpoint

if TYPE_CHECKING:
    from stitch.sdk.config import Profile


class StitchClient:
    def __init__(
        self,
        profile: Profile,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._profile = profile
        headers = resolve_auth(profile, env_token=os.environ.get("STITCH_TOKEN"))
        self._http = httpx.AsyncClient(
            base_url=profile.server, headers=headers, transport=transport
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def query(
        self,
        resource_type: str,
        verb: str,
        resource_id: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> QueryResult:
        method, path = resolve_endpoint(resource_type, verb, resource_id)
        response = await self._http.request(method, path, params=params)
        self._check_response(response)
        data = response.json()
        if isinstance(data, list):
            return QueryResult(items=data, total=len(data))
        return QueryResult(items=[data], total=1)

    async def command(
        self,
        resource_type: str,
        verb: str,
        resource_id: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        method, path = resolve_endpoint(resource_type, verb, resource_id)
        response = await self._http.request(method, path, json=params)
        self._check_response(response)
        return response.json()

    def _check_response(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            try:
                body = response.json()
            except (ValueError, KeyError):
                error = TransportError(
                    kind="http_error",
                    message=f"HTTP {response.status_code}",
                    retryable=response.status_code >= 500,
                )
                raise StitchTransportError(error) from None
            error = StitchError(
                code=body.get("code", f"http.{response.status_code}"),
                message=body.get("message", body.get("detail", "Unknown error")),
                retryable=body.get("retryable", response.status_code >= 500),
            )
            raise StitchAPIError(error)
