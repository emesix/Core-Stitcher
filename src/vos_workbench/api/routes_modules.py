from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException

from vos_workbench.api.responses import ApiResponse

if TYPE_CHECKING:
    from vos_workbench.runtime.runtime import Runtime


def create_module_routes(runtime: Runtime) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.get("/modules")
    async def list_modules() -> ApiResponse:
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
        return ApiResponse(data=modules)

    @router.get("/modules/{module_uuid}")
    async def get_module(module_uuid: str) -> ApiResponse:
        mod = runtime.get_module_by_uuid(module_uuid)
        if mod is None:
            raise HTTPException(status_code=404, detail="Module not found")
        return ApiResponse(
            data={
                "uuid": str(mod.uuid),
                "name": mod.name,
                "type": mod.type,
                "family": mod.family.value,
                "lifecycle": mod.lifecycle,
                "enabled": mod.enabled,
                "config": mod.config,
                "wiring": mod.wiring.model_dump(),
            }
        )

    return router
