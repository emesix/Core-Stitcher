from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter

from stitch_workbench.api.responses import ApiResponse

if TYPE_CHECKING:
    from stitch_workbench.runtime.runtime import Runtime


def create_project_routes(runtime: Runtime) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.get("/project")
    async def get_project() -> ApiResponse:
        cfg = runtime.workbench_config
        return ApiResponse(
            data={
                "id": cfg.project.id,
                "name": cfg.project.name,
                "version": cfg.project.version,
                "schema_version": cfg.schema_version,
            }
        )

    @router.get("/tree/config")
    async def get_config_tree() -> ApiResponse:
        modules = [
            {
                "uuid": str(m.uuid),
                "name": m.name,
                "type": m.type,
                "family": m.family.value,
                "lifecycle": m.lifecycle,
                "enabled": m.enabled,
            }
            for m in runtime.module_configs
        ]
        return ApiResponse(data={"modules": modules})

    return router
