"""HTTP routes for preflight verification, tracing, impact, and system health.

Exposes the PreflightWorkflowProtocol and runtime health as REST endpoints.
interfacekit resolves the workflow facade — it never imports low-level modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from stitch.modelkit.impact import ImpactRequest  # noqa: TC001 (FastAPI runtime)
from stitch.modelkit.trace import TraceRequest  # noqa: TC001 (FastAPI runtime)
from stitch.modelkit.verification import VerificationReport  # noqa: TC001 (FastAPI runtime)
from stitch.verifykit.diff import diff_reports


class DiffRequest(BaseModel):
    before: VerificationReport
    after: VerificationReport

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from stitch.contractkit.workflow import PreflightWorkflowProtocol


def create_preflight_router(workflow: PreflightWorkflowProtocol) -> APIRouter:
    router = APIRouter(tags=["preflight"])

    @router.post("/verify")
    async def run_verification():
        try:
            report = await workflow.run_verification()
            return report.model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/topology")
    async def get_declared_topology():
        declared_topology = getattr(workflow, "declared_topology", None)
        if declared_topology is None:
            raise HTTPException(status_code=501, detail="Topology access not available")
        return declared_topology.model_dump(mode="json")

    @router.post("/trace")
    async def run_trace(request: TraceRequest):
        try:
            result = await workflow.run_trace(request)
            return result.model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/impact")
    async def run_impact_preview(request: ImpactRequest):
        try:
            result = await workflow.run_impact_preview(request)
            return result.model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/diff")
    async def run_diff(request: DiffRequest):
        result = diff_reports(request.before, request.after)
        return result.model_dump(mode="json")

    return router


def create_health_router(
    health_fn: Callable[[], Coroutine[Any, Any, dict]],
) -> APIRouter:
    """Create a health router backed by a callable that returns aggregated module health."""
    router = APIRouter(tags=["health"])

    @router.get("/health/modules")
    async def module_health():
        return await health_fn()

    return router
