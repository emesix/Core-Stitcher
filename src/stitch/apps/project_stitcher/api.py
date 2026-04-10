"""HTTP API routes for Project Explorer."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from uuid import UUID  # noqa: TC003 (FastAPI needs UUID at runtime for path params)

from fastapi import APIRouter, HTTPException

from stitch.agentcore.orchestration import RunOrchestrator
from stitch.agentcore.plannerkit import WorkRequest, plan_request
from stitch.agentcore.reviewkit import ReviewRequest
from stitch.agentcore.storekit import RunRecord, RunStatus, TaskExecution

if TYPE_CHECKING:
    from stitch.agentcore.executorkit.protocol import ReviewableExecutorProtocol
    from stitch.agentcore.registry import ExecutorRegistry
    from stitch.agentcore.storekit import JsonRunStore


def create_router(
    store: JsonRunStore,
    registry: ExecutorRegistry,
) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health():
        return {"status": "ok", "executors": len(registry)}

    @router.post("/runs")
    async def create_run(request: WorkRequest):
        plan = plan_request(request)
        run = RunRecord(
            status=RunStatus.PLANNED,
            request=request,
            plan=plan,
        )
        store.save(run)
        return {
            "run_id": str(run.run_id),
            "status": run.status,
            "tasks": len(plan.tasks),
        }

    @router.get("/runs")
    async def list_runs():
        runs = store.list_runs()
        return [
            {
                "run_id": str(r.run_id),
                "status": r.status,
                "description": r.request.description if r.request else None,
                "tasks": len(r.plan.tasks) if r.plan else 0,
                "created_at": r.created_at.isoformat(),
            }
            for r in runs
        ]

    @router.get("/runs/{run_id}")
    async def get_run(run_id: UUID):
        run = store.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return run.model_dump(mode="json")

    @router.post("/runs/{run_id}/execute")
    async def execute_run(run_id: UUID):
        run = store.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if run.plan is None:
            raise HTTPException(status_code=400, detail="Run has no plan")

        run.status = RunStatus.EXECUTING
        executions = []

        for task in run.plan.execution_order():
            from stitch.agentcore.taskkit import TaskRecord

            record = TaskRecord(
                description=task.description,
                domain=task.domain,
                priority=task.priority,
            )
            matches = registry.find_for_task(record)
            if not matches:
                executions.append(
                    TaskExecution(
                        task_id=task.task_id,
                        description=task.description,
                        domain=task.domain,
                    )
                )
                continue

            executor = matches[0]
            outcome = await executor.execute(record)
            executions.append(
                TaskExecution(
                    task_id=task.task_id,
                    description=task.description,
                    domain=task.domain,
                    executor_id=executor.executor_id,
                    outcome=outcome,
                )
            )

        run.executions = executions
        run.status = RunStatus.COMPLETED
        store.save(run)

        return {
            "run_id": str(run.run_id),
            "status": run.status,
            "executed": len([e for e in executions if e.outcome]),
            "skipped": len([e for e in executions if not e.outcome]),
        }

    @router.post("/runs/{run_id}/review")
    async def review_run(run_id: UUID):
        run = store.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")

        run.status = RunStatus.REVIEWING
        executors = registry.list_all()
        if not executors:
            raise HTTPException(status_code=503, detail="No executor available for review")

        reviewer = executors[0]
        if not hasattr(reviewer, "review"):
            raise HTTPException(status_code=503, detail="Executor does not support review")

        review_req = ReviewRequest(
            plan_id=run.plan.plan_id if run.plan else None,
            content={"executions": [e.model_dump(mode="json") for e in run.executions]},
            criteria=["correctness", "completeness"],
        )

        reviewable = cast("ReviewableExecutorProtocol", reviewer)
        result = await reviewable.review(review_req)
        run.reviews.append(result)
        run.status = RunStatus.COMPLETED
        store.save(run)

        return {
            "run_id": str(run.run_id),
            "verdict": result.verdict,
            "findings": len(result.findings),
            "summary": result.summary,
        }

    @router.post("/runs/{run_id}/orchestrate")
    async def orchestrate_run(run_id: UUID):
        orchestrator = RunOrchestrator(registry, store)
        try:
            run = await orchestrator.orchestrate(str(run_id))
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        return {
            "run_id": str(run.run_id),
            "status": run.status,
            "executed": len([e for e in run.executions if e.outcome]),
            "summary": run.summary,
            "review_verdict": run.reviews[0].verdict if run.reviews else None,
            "review_findings": len(run.reviews[0].findings) if run.reviews else 0,
        }

    return router
