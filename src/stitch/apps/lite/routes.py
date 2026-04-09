"""Stitch Lite routes — server-rendered HTML pages."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse


def create_routes() -> APIRouter:
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        templates = request.app.state.templates
        return templates.TemplateResponse(request, "index.html")

    @router.get("/devices", response_class=HTMLResponse)
    async def device_list(request: Request) -> HTMLResponse:
        client = request.app.state.client
        result = await client.query("device", "list")
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request,
            "devices.html",
            {"devices": result.items, "active": "devices", "subtitle": "Devices"},
        )

    @router.get("/devices/{device_id}", response_class=HTMLResponse)
    async def device_detail(request: Request, device_id: str) -> HTMLResponse:
        client = request.app.state.client
        result = await client.query("device", "show", resource_id=device_id)
        device = result.items[0] if result.items else {}
        neighbors = await client.query("device", "neighbors", resource_id=device_id)
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request,
            "device_detail.html",
            {
                "device": device,
                "neighbors": neighbors.items,
                "active": "devices",
                "subtitle": device.get("name", device_id),
            },
        )

    return router
