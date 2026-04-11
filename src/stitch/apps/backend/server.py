"""Stitch backend server -- unified API for all clients."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from stitch.interfacekit.explorer_routes import create_explorer_router
from stitch.interfacekit.routes import create_health_router, create_preflight_router
from stitch.storekit import load_topology


def create_app(topology_path: str | None = None) -> FastAPI:
    topo_path = Path(topology_path or "topologies/lab.json")
    topo = load_topology(topo_path)

    from stitch.apps.backend.workflow import BackendWorkflow

    workflow = BackendWorkflow(topo, topo_path)

    app = FastAPI(title="Stitch Backend", version="1.0")

    # Explorer routes (devices, topology, neighbors, vlans, diagnostics)
    app.include_router(create_explorer_router(workflow), prefix="/api/v1/explorer")

    # Preflight routes (verify, trace, impact, diff)
    app.include_router(create_preflight_router(workflow), prefix="/api/v1")

    # Health + system probes
    app.include_router(create_health_router(workflow.health), prefix="/api/v1")

    @app.get("/api/v1/health")
    async def system_health():
        return {"status": "ok"}

    @app.get("/api/v1/readyz")
    async def readyz():
        return {"ready": True, "topology": str(topo_path)}

    @app.get("/api/v1/livez")
    async def livez():
        return {"alive": True, "version": "1.0"}

    # Project-stitcher run API
    from stitch.agentcore.bootstrap import build_alpha_registry
    from stitch.agentcore.storekit import JsonRunStore
    from stitch.apps.project_stitcher.api import create_router as create_run_router

    registry, routing = build_alpha_registry()
    run_store = JsonRunStore(Path.home() / ".stitch" / "runs")
    app.include_router(
        create_run_router(run_store, registry, routing=routing), prefix="/api/v1"
    )

    return app


def main() -> None:
    parser = argparse.ArgumentParser(prog="stitch-server")
    parser.add_argument("--topology", default="topologies/lab.json")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    app = create_app(topology_path=args.topology)
    uvicorn.run(app, host=args.host, port=args.port)
