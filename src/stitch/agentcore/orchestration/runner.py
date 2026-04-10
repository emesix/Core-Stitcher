"""RunOrchestrator — chains domain execution + AI summary + AI review.

Produces a full audit trail via StepRecords. Supports feedback loops:
when review rejects, creates correction steps and re-reviews up to
max_corrections times. Uses health-aware executor selection and
escalation policy (REUSE → SWITCH → STOP) on repeated failures.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from stitch.agentcore.orchestration.budget import BudgetPolicy, EscalationAction
from stitch.agentcore.reviewkit.models import ReviewRequest, ReviewVerdict
from stitch.agentcore.storekit.models import (
    ExecutorSelection,
    RunStatus,
    SelectionReason,
    StepKind,
    StepRecord,
    StepStatus,
    TaskExecution,
)
from stitch.agentcore.taskkit.models import TaskRecord, TaskStatus

if TYPE_CHECKING:
    from stitch.agentcore.executorkit.protocol import (
        ExecutorProtocol,
        ReviewableExecutorProtocol,
    )
    from stitch.agentcore.registry.executor_registry import ExecutorRegistry
    from stitch.agentcore.storekit.json_store import JsonRunStore
    from stitch.agentcore.storekit.models import RunRecord


class OrchestrationError(Exception):
    pass


class RunOrchestrator:
    """Chains domain + AI execution with budget-aware feedback loop."""

    def __init__(
        self,
        registry: ExecutorRegistry,
        store: JsonRunStore,
        policy: BudgetPolicy | None = None,
    ) -> None:
        self._registry = registry
        self._store = store
        self._policy = policy or BudgetPolicy()
        self._ai_steps_used = 0
        self._executor_failures: dict[str, int] = {}

    async def orchestrate(self, run_id: str) -> RunRecord:
        from uuid import UUID

        run = self._store.get(UUID(run_id))
        if run is None:
            raise OrchestrationError(f"Run {run_id} not found")
        if run.plan is None:
            raise OrchestrationError("Run has no plan")

        run.status = RunStatus.EXECUTING
        run.steps = []
        self._ai_steps_used = 0
        self._executor_failures = {}

        # Step 1: Execute domain tasks
        executions = await self._execute_domain_tasks(run)
        run.executions = executions

        # Step 2: AI summary (budget-gated)
        domain_results = [
            e for e in executions if e.outcome and e.outcome.status == TaskStatus.COMPLETED
        ]
        if domain_results and self._policy.allow_ai_summary:
            if self._can_use_ai_step(run):
                run.summary = await self._summarize(domain_results, run, iteration=0)
            else:
                self._record_budget_skip(run, StepKind.AI_SUMMARY, 0)

        # Step 3: Review + feedback loop (budget-gated)
        run.status = RunStatus.REVIEWING
        corrections_done = 0

        if self._policy.allow_ai_review:
            for iteration in range(self._policy.max_reviews):
                if not self._can_use_ai_step(run):
                    self._record_budget_skip(run, StepKind.AI_REVIEW, iteration)
                    break

                review = await self._review(run, iteration=iteration)
                if review is None:
                    # Review failed (executor error) — escalation decides next action
                    action = self._check_escalation("__ai_review__")
                    if action == EscalationAction.STOP:
                        break
                    # REUSE or SWITCH: continue to next iteration (new executor selected)
                    continue

                run.reviews.append(review)

                if review.verdict == ReviewVerdict.APPROVE:
                    break

                # Check correction budget
                if not self._policy.can_correct(corrections_done):
                    self._record_budget_skip(run, StepKind.CORRECTION, iteration + 1)
                    break

                if not self._can_use_ai_step(run):
                    self._record_budget_skip(run, StepKind.CORRECTION, iteration + 1)
                    break

                correction = await self._correct(run, review, iteration=iteration)
                if correction:
                    run.summary = correction
                    corrections_done += 1

        run.status = RunStatus.COMPLETED
        run.updated_at = datetime.now(UTC)
        self._store.save(run)
        return run

    def _can_use_ai_step(self, run: RunRecord) -> bool:
        return self._policy.can_run_ai_step(self._ai_steps_used)

    def _record_budget_skip(self, run: RunRecord, kind: StepKind, iteration: int) -> None:
        run.steps.append(
            StepRecord(
                kind=kind,
                status=StepStatus.SKIPPED,
                description=f"Skipped by budget policy (ai_steps={self._ai_steps_used})",
                iteration=iteration,
                selection=ExecutorSelection(reason=SelectionReason.BUDGET_EXHAUSTED),
                started_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
            )
        )

    async def _execute_domain_tasks(self, run: RunRecord) -> list[TaskExecution]:
        executions: list[TaskExecution] = []
        assert run.plan is not None

        for task in run.plan.execution_order():
            started = datetime.now(UTC)
            record = TaskRecord(
                description=task.description,
                domain=task.domain,
                priority=task.priority,
                metadata=run.request.metadata if run.request else {},
            )

            executor, selection = await self._select_executor(record)

            if executor is None:
                run.steps.append(
                    StepRecord(
                        kind=StepKind.DOMAIN_CALL,
                        status=StepStatus.SKIPPED,
                        description=task.description,
                        selection=selection,
                        started_at=started,
                        finished_at=datetime.now(UTC),
                    )
                )
                executions.append(
                    TaskExecution(
                        task_id=task.task_id,
                        description=task.description,
                        domain=task.domain,
                    )
                )
                continue

            try:
                outcome = await executor.execute(record)
                is_ok = outcome.status == TaskStatus.COMPLETED
                status = StepStatus.COMPLETED if is_ok else StepStatus.FAILED
                if not is_ok:
                    self._record_executor_failure(executor.executor_id)
                run.steps.append(
                    StepRecord(
                        kind=StepKind.DOMAIN_CALL,
                        status=status,
                        description=task.description,
                        selection=selection,
                        result=outcome.result if is_ok else None,
                        error=outcome.error if not is_ok else None,
                        started_at=started,
                        finished_at=datetime.now(UTC),
                    )
                )
            except Exception as e:
                outcome = None
                self._record_executor_failure(executor.executor_id)
                run.steps.append(
                    StepRecord(
                        kind=StepKind.DOMAIN_CALL,
                        status=StepStatus.FAILED,
                        description=task.description,
                        selection=selection,
                        error=str(e),
                        started_at=started,
                        finished_at=datetime.now(UTC),
                    )
                )

            executions.append(
                TaskExecution(
                    task_id=task.task_id,
                    description=task.description,
                    domain=task.domain,
                    executor_id=executor.executor_id,
                    outcome=outcome,
                )
            )

        return executions

    async def _summarize(
        self,
        domain_results: list[TaskExecution],
        run: RunRecord,
        *,
        iteration: int = 0,
    ) -> str | None:
        started = datetime.now(UTC)
        ai_executor = await self._find_ai_executor()

        if ai_executor is None:
            run.steps.append(
                StepRecord(
                    kind=StepKind.AI_SUMMARY,
                    status=StepStatus.SKIPPED,
                    description="No general-purpose executor available",
                    selection=ExecutorSelection(reason=SelectionReason.NO_EXECUTOR),
                    iteration=iteration,
                    started_at=started,
                    finished_at=datetime.now(UTC),
                )
            )
            return None

        results_text = "\n".join(
            f"- {e.description}: {json.dumps(e.outcome.result)}"
            for e in domain_results
            if e.outcome is not None
        )
        summary_task = TaskRecord(
            description=f"Summarize these domain results:\n{results_text}",
            metadata={"action": "summarize"},
        )

        selection = ExecutorSelection(
            executor_id=ai_executor.executor_id,
            reason=SelectionReason.GENERAL_FALLBACK,
            candidates_considered=len(self._registry.list_all()),
        )

        try:
            outcome = await ai_executor.execute(summary_task)
            self._ai_steps_used += 1
            run.steps.append(
                StepRecord(
                    kind=StepKind.AI_SUMMARY,
                    status=StepStatus.COMPLETED,
                    description="AI summary of domain results",
                    selection=selection,
                    iteration=iteration,
                    result=str(outcome.result) if outcome.result else None,
                    started_at=started,
                    finished_at=datetime.now(UTC),
                )
            )
            return str(outcome.result) if outcome.status == TaskStatus.COMPLETED else None
        except Exception as e:
            self._record_executor_failure(ai_executor.executor_id)
            run.steps.append(
                StepRecord(
                    kind=StepKind.AI_SUMMARY,
                    status=StepStatus.FAILED,
                    description="AI summary failed",
                    selection=selection,
                    iteration=iteration,
                    error=str(e),
                    started_at=started,
                    finished_at=datetime.now(UTC),
                )
            )
            return None

    async def _review(self, run: RunRecord, *, iteration: int = 0):
        started = datetime.now(UTC)
        ai_executor = await self._find_ai_executor()

        if ai_executor is None or not hasattr(ai_executor, "review"):
            run.steps.append(
                StepRecord(
                    kind=StepKind.AI_REVIEW,
                    status=StepStatus.SKIPPED,
                    description="No executor available for review",
                    selection=ExecutorSelection(reason=SelectionReason.NO_EXECUTOR),
                    iteration=iteration,
                    started_at=started,
                    finished_at=datetime.now(UTC),
                )
            )
            return None

        selection = ExecutorSelection(
            executor_id=ai_executor.executor_id,
            reason=SelectionReason.GENERAL_FALLBACK,
            candidates_considered=len(self._registry.list_all()),
        )

        review_req = ReviewRequest(
            plan_id=run.plan.plan_id if run.plan else None,
            content={
                "request": run.request.description if run.request else "",
                "executions": [e.model_dump(mode="json") for e in run.executions],
                "summary": run.summary,
                "iteration": iteration,
            },
            criteria=["correctness", "completeness", "actionability"],
        )

        reviewer = cast("ReviewableExecutorProtocol", ai_executor)
        try:
            result = await reviewer.review(review_req)
            self._ai_steps_used += 1
            run.steps.append(
                StepRecord(
                    kind=StepKind.AI_REVIEW,
                    status=StepStatus.COMPLETED,
                    description=f"AI review (iteration {iteration})",
                    selection=selection,
                    iteration=iteration,
                    result=result.verdict,
                    started_at=started,
                    finished_at=datetime.now(UTC),
                )
            )
            return result
        except Exception as e:
            self._record_executor_failure(ai_executor.executor_id)
            run.steps.append(
                StepRecord(
                    kind=StepKind.AI_REVIEW,
                    status=StepStatus.FAILED,
                    description="AI review failed",
                    selection=selection,
                    iteration=iteration,
                    error=str(e),
                    started_at=started,
                    finished_at=datetime.now(UTC),
                )
            )
            return None

    async def _correct(self, run: RunRecord, review, *, iteration: int) -> str | None:
        started = datetime.now(UTC)
        ai_executor = await self._find_ai_executor()

        if ai_executor is None:
            run.steps.append(
                StepRecord(
                    kind=StepKind.CORRECTION,
                    status=StepStatus.SKIPPED,
                    description="No executor available for correction",
                    selection=ExecutorSelection(reason=SelectionReason.NO_EXECUTOR),
                    iteration=iteration + 1,
                    started_at=started,
                    finished_at=datetime.now(UTC),
                )
            )
            return None

        findings_text = "\n".join(
            f"- [{f.severity}] {f.description}"
            + (f" (suggestion: {f.suggestion})" if f.suggestion else "")
            for f in review.findings
        )

        correction_task = TaskRecord(
            description=(
                f"Previous output was reviewed and received verdict: {review.verdict}.\n"
                f"Findings:\n{findings_text}\n\n"
                f"Previous summary:\n{run.summary or '(none)'}\n\n"
                f"Please produce a corrected version addressing the review findings."
            ),
            metadata={"action": "correction", "iteration": iteration + 1},
        )

        selection = ExecutorSelection(
            executor_id=ai_executor.executor_id,
            reason=SelectionReason.GENERAL_FALLBACK,
            candidates_considered=len(self._registry.list_all()),
        )

        try:
            outcome = await ai_executor.execute(correction_task)
            self._ai_steps_used += 1
            run.steps.append(
                StepRecord(
                    kind=StepKind.CORRECTION,
                    status=StepStatus.COMPLETED,
                    description=f"Correction based on review findings (iteration {iteration + 1})",
                    selection=selection,
                    iteration=iteration + 1,
                    result=str(outcome.result) if outcome.result else None,
                    started_at=started,
                    finished_at=datetime.now(UTC),
                )
            )
            return str(outcome.result) if outcome.status == TaskStatus.COMPLETED else None
        except Exception as e:
            self._record_executor_failure(ai_executor.executor_id)
            run.steps.append(
                StepRecord(
                    kind=StepKind.CORRECTION,
                    status=StepStatus.FAILED,
                    description="Correction failed",
                    selection=selection,
                    iteration=iteration + 1,
                    error=str(e),
                    started_at=started,
                    finished_at=datetime.now(UTC),
                )
            )
            return None

    async def _select_executor(
        self, task: TaskRecord
    ) -> tuple[ExecutorProtocol | None, ExecutorSelection]:
        all_matches = self._registry.find_for_task(task)

        # Filter to healthy executors (skip those that have failed too many times)
        healthy = await self._filter_healthy(all_matches)

        domain_matches = [
            m for m in healthy if task.domain and task.domain in m.capability.domains
        ]

        if domain_matches:
            return domain_matches[0], ExecutorSelection(
                executor_id=domain_matches[0].executor_id,
                reason=SelectionReason.DOMAIN_MATCH,
                candidates_considered=len(all_matches),
                domain_matches=len(domain_matches),
            )

        if healthy:
            return healthy[0], ExecutorSelection(
                executor_id=healthy[0].executor_id,
                reason=SelectionReason.GENERAL_FALLBACK,
                candidates_considered=len(all_matches),
                domain_matches=0,
            )

        return None, ExecutorSelection(
            reason=SelectionReason.NO_EXECUTOR,
            candidates_considered=len(all_matches),
        )

    async def _filter_healthy(
        self, executors: list[ExecutorProtocol]
    ) -> list[ExecutorProtocol]:
        """Filter executors to those reporting ok/degraded health."""
        healthy: list[ExecutorProtocol] = []
        for executor in executors:
            try:
                h = await executor.health()
                if h.status in ("ok", "degraded"):
                    healthy.append(executor)
            except Exception:
                continue
        return healthy

    async def _find_ai_executor(self) -> ExecutorProtocol | None:
        """Find a general-purpose AI executor, preferring local if policy says so."""
        candidates = [e for e in self._registry.list_all() if not e.capability.domains]
        if not candidates:
            return None

        # Filter to healthy, but fall back to all candidates if none are healthy
        healthy = await self._filter_healthy(candidates)
        pool = healthy or candidates

        if self._policy.prefer_local:
            local = [e for e in pool if "local" in e.capability.tags]
            available_local = [
                e
                for e in local
                if not hasattr(e, "available") or e.available is not False  # type: ignore[attr-defined]
            ]
            if available_local:
                return available_local[0]

        # Apply escalation: skip executors that have failed too many times
        for executor in pool:
            action = self._policy.should_escalate(
                self._executor_failures.get(executor.executor_id, 0)
            )
            if action != EscalationAction.STOP:
                return executor

        return pool[0] if pool else None

    def _record_executor_failure(self, executor_id: str) -> None:
        self._executor_failures[executor_id] = (
            self._executor_failures.get(executor_id, 0) + 1
        )

    def _check_escalation(self, executor_id: str) -> EscalationAction:
        failures = self._executor_failures.get(executor_id, 0)
        return self._policy.should_escalate(failures)
