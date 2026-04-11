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

    # --- Devices ---

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
        # Flatten ports dict into a list for template iteration
        if isinstance(device.get("ports"), dict):
            device["ports"] = [
                {"name": name, **port} for name, port in device["ports"].items()
            ]
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

    # --- Preflight ---

    @router.get("/preflight", response_class=HTMLResponse)
    async def preflight_page(request: Request) -> HTMLResponse:
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request,
            "preflight.html",
            {"active": "runs", "subtitle": "Preflight"},
        )

    @router.post("/preflight/run", response_class=HTMLResponse)
    async def preflight_run(request: Request) -> HTMLResponse:
        client = request.app.state.client
        form = await request.form()
        scope = form.get("scope", None)
        params = {"scope": scope} if scope else None
        raw = await client.command("preflight", "run", params=params)
        # Transform VerificationReport into template-friendly shape
        summary = raw.get("summary", {})
        checks = []
        for link_result in raw.get("results", []):
            for check in link_result.get("checks", []):
                checks.append({
                    "name": check.get("check", link_result.get("link", "-")),
                    "status": check.get("flag", "info"),
                    "message": check.get("message", "-"),
                })
        result = {
            "total": summary.get("total", 0),
            "ok": summary.get("pass", 0),
            "warning": summary.get("warning", 0),
            "error": summary.get("fail", 0),
            "checks": checks,
        }
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request,
            "preflight_result.html",
            {"result": result, "active": "runs", "subtitle": "Preflight Result"},
        )

    # --- Runs ---

    @router.get("/runs", response_class=HTMLResponse)
    async def run_list(request: Request) -> HTMLResponse:
        client = request.app.state.client
        result = await client.query("run", "list")
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request,
            "runs.html",
            {"runs": result.items, "active": "runs", "subtitle": "Runs"},
        )

    @router.get("/runs/{run_id}", response_class=HTMLResponse)
    async def run_detail(request: Request, run_id: str) -> HTMLResponse:
        client = request.app.state.client
        result = await client.query("run", "show", resource_id=run_id)
        run = result.items[0] if result.items else {}
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request,
            "run_detail.html",
            {"run": run, "active": "runs", "subtitle": f"Run {run_id}"},
        )

    # --- Reviews ---

    @router.get("/reviews", response_class=HTMLResponse)
    async def review_list(request: Request) -> HTMLResponse:
        client = request.app.state.client
        result = await client.query("run", "list")
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request,
            "reviews.html",
            {"reviews": result.items, "active": "reviews", "subtitle": "Reviews"},
        )

    @router.get("/reviews/{review_id}", response_class=HTMLResponse)
    async def review_detail(request: Request, review_id: str) -> HTMLResponse:
        client = request.app.state.client
        result = await client.query("run", "show", resource_id=review_id)
        review = result.items[0] if result.items else {}
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request,
            "review_detail.html",
            {"review": review, "active": "reviews", "subtitle": f"Review {review_id}"},
        )

    @router.post("/reviews/{review_id}/approve", response_class=HTMLResponse)
    async def review_approve(request: Request, review_id: str) -> HTMLResponse:
        client = request.app.state.client
        form = await request.form()
        comment = form.get("comment", "")
        await client.command(
            "run",
            "review",
            resource_id=review_id,
            params={"action": "approve", "comment": comment},
        )
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request,
            "review_approved.html",
            {"review_id": review_id, "active": "reviews", "subtitle": "Approved"},
        )

    @router.post("/reviews/{review_id}/reject", response_class=HTMLResponse)
    async def review_reject(request: Request, review_id: str) -> HTMLResponse:
        client = request.app.state.client
        form = await request.form()
        comment = form.get("comment", "")
        await client.command(
            "run",
            "review",
            resource_id=review_id,
            params={"action": "reject", "comment": comment},
        )
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request,
            "review_rejected.html",
            {"review_id": review_id, "active": "reviews", "subtitle": "Rejected"},
        )

    # --- Topology ---

    @router.get("/topology", response_class=HTMLResponse)
    async def topology_page(request: Request) -> HTMLResponse:
        client = request.app.state.client
        result = await client.query("topology", "show")
        topo = result.items[0] if result.items else {}
        # Flatten devices dict into a list for template iteration
        if isinstance(topo.get("devices"), dict):
            topo["devices"] = [
                {"id": dev_id, **dev} for dev_id, dev in topo["devices"].items()
            ]
        # Extract topology name from meta
        if "meta" in topo and isinstance(topo["meta"], dict):
            topo.setdefault("name", topo["meta"].get("name"))
            topo.setdefault("updated_at", topo["meta"].get("updated_at"))
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request,
            "topology.html",
            {
                "topology": topo,
                "active": "topology",
                "subtitle": "Topology",
            },
        )

    # --- System ---

    @router.get("/system", response_class=HTMLResponse)
    async def system_page(request: Request) -> HTMLResponse:
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request,
            "system.html",
            {"active": "system", "subtitle": "System"},
        )

    return router
