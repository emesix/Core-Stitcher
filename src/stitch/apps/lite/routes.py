"""Stitch Lite routes — server-rendered HTML pages."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse


def create_routes() -> APIRouter:
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        templates = request.app.state.templates
        return templates.TemplateResponse(
            "index.html", {"request": request, "title": "Stitch Lite"}
        )

    return router
