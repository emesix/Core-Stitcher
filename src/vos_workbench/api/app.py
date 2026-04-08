from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from vos_workbench.api.responses import ApiResponse
from vos_workbench.api.routes_events import create_event_routes
from vos_workbench.api.routes_modules import create_module_routes
from vos_workbench.api.routes_project import create_project_routes
from vos_workbench.runtime.runtime import Runtime

if TYPE_CHECKING:
    from pathlib import Path


def create_app(project_root: Path | None = None, db_url: str | None = None) -> FastAPI:
    app = FastAPI(
        title="VOS-Workbench",
        description="Modular headless agentic backend",
        version="0.1.0",
    )

    # livez — always available, no runtime needed
    @app.get("/api/v1/livez")
    async def livez() -> JSONResponse:
        return JSONResponse(content={"status": "alive"}, status_code=200)

    if project_root is not None:
        effective_db_url = db_url or f"sqlite:///{project_root / 'vos_workbench.db'}"
        runtime = Runtime(project_root, db_url=effective_db_url)
        runtime.load()
        app.state.runtime = runtime

        @app.get("/api/v1/readyz")
        async def readyz_with_runtime() -> JSONResponse:
            result = runtime.is_ready()
            status_code = 200 if result["status"] == "ready" else 503
            return JSONResponse(content=result, status_code=status_code)

        @app.get("/api/v1/health")
        async def health_with_runtime() -> ApiResponse:
            return ApiResponse(data=runtime.get_health())

        app.include_router(create_project_routes(runtime))
        app.include_router(create_module_routes(runtime))
        app.include_router(create_event_routes(runtime))
    else:

        @app.get("/api/v1/readyz")
        async def readyz_no_runtime() -> JSONResponse:
            return JSONResponse(
                content={
                    "status": "not_ready",
                    "booted": False,
                    "startup_plan_complete": False,
                    "db_reachable": False,
                    "failed_modules": [],
                },
                status_code=503,
            )

        @app.get("/api/v1/health")
        async def health_minimal() -> ApiResponse:
            return ApiResponse(data={"status": "ok", "booted": False})

    return app
