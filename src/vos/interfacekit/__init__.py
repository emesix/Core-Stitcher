"""interfacekit — Integration module exposing HTTP API and MCP tool endpoints.

Mounts a FastAPI router at a configurable prefix and registers MCP tool handlers
so that external agents can query topology, trigger verification, and run traces.
Provides the 'http_api' and 'mcp_tools' capabilities; requires 'preflight_workflow'.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from vos.contractkit.explorer import ExplorerWorkflowProtocol
from vos.contractkit.workflow import PreflightWorkflowProtocol
from vos.interfacekit.explorer_routes import create_explorer_router
from vos.interfacekit.routes import create_preflight_router
from vos_workbench.sdk import ModuleContext, ModuleManifest

if TYPE_CHECKING:
    from fastapi import APIRouter


class InterfacekitConfig(BaseModel):
    api_prefix: str = "/api/v1"


class InterfacekitModule:
    type_name = "integration.interfacekit"
    version = "0.1.0"
    config_model = InterfacekitConfig
    manifest = ModuleManifest(
        capabilities_provided=["http_api", "mcp_tools"],
        capabilities_required=["preflight_workflow"],
    )

    def __init__(self) -> None:
        self._context: ModuleContext | None = None
        self._router: APIRouter | None = None
        self._has_explorer: bool = False

    async def start(self, context: ModuleContext) -> None:
        from fastapi import APIRouter as _Router

        self._context = context

        router = _Router()
        router.include_router(
            create_preflight_router(
                context.capabilities.resolve_one(PreflightWorkflowProtocol)
            )
        )

        explorer_workflows = context.capabilities.resolve_all(ExplorerWorkflowProtocol)
        if explorer_workflows:
            router.include_router(
                create_explorer_router(explorer_workflows[0]), prefix="/explorer"
            )
            self._has_explorer = True

        self._router = router

    async def stop(self) -> None:
        self._router = None
        self._has_explorer = False

    async def health(self) -> dict[str, Any]:
        if self._router is None:
            return {"status": "error", "message": "Module not started"}
        return {"status": "ok", "explorer": self._has_explorer}

    @property
    def router(self) -> APIRouter | None:
        return self._router


__all__ = [
    "InterfacekitConfig",
    "InterfacekitModule",
    "create_explorer_router",
    "create_preflight_router",
]
