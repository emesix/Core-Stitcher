"""OPNsense API routes — FastAPI router for live OPNsense data via gateway."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from stitch.apps.backend.opnsense_models import OpnsenseSummary
from stitch.apps.backend.opnsense_service import OpnsenseService


def create_opnsense_router(gateway_url: str | None = None) -> APIRouter:
    """Factory: creates an OPNsense router with its own service instance."""
    router = APIRouter(tags=["opnsense"])
    service = OpnsenseService(gateway_url=gateway_url)

    @router.get("/summary", response_model=OpnsenseSummary)
    async def summary() -> OpnsenseSummary:
        return await service.get_summary()

    @router.get("/interfaces")
    async def interfaces() -> list[dict[str, Any]]:
        return await service.get_interfaces()

    @router.get("/routes")
    async def routes() -> list[dict[str, Any]]:
        return await service.get_routes()

    @router.get("/aliases")
    async def aliases() -> list[dict[str, Any]]:
        return await service.get_aliases()

    @router.get("/nat")
    async def nat() -> dict[str, Any]:
        return await service.get_nat()

    @router.get("/vlans")
    async def vlans() -> list[dict[str, Any]]:
        return await service.get_vlans()

    @router.get("/bridges")
    async def bridges() -> list[dict[str, Any]]:
        return await service.get_bridges()

    return router
