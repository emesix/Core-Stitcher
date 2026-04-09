"""Tests for RunOrchestrator — mixed workflow with feedback loop and audit trail."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from vos.agentcore.executorkit.mock import MockExecutor
from vos.agentcore.executorkit.protocol import ExecutorCapability
from vos.agentcore.orchestration import (
    BudgetPolicy,
    RunOrchestrator,
    SelectionReason,
    StepKind,
    StepStatus,
)
from vos.agentcore.orchestration.runner import OrchestrationError
from vos.agentcore.plannerkit import WorkRequest, plan_request
from vos.agentcore.registry import ExecutorRegistry
from vos.agentcore.reviewkit import ReviewVerdict
from vos.agentcore.storekit import JsonRunStore, RunRecord, RunStatus

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def store(tmp_path: Path) -> JsonRunStore:
    return JsonRunStore(tmp_path / "runs")


@pytest.fixture()
def registry() -> ExecutorRegistry:
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo-exec", domains=["topology"]))
    reg.register(MockExecutor("ai-exec"))  # general purpose, approves by default
    return reg


def _create_run(store: JsonRunStore, **req_kwargs) -> str:
    request = WorkRequest(**req_kwargs)
    plan = plan_request(request)
    run = RunRecord(status=RunStatus.PLANNED, request=request, plan=plan)
    store.save(run)
    return str(run.run_id)


# --- Basic orchestration (no corrections needed) ---


async def test_orchestrate_completes(store: JsonRunStore, registry: ExecutorRegistry):
    run_id = _create_run(store, description="verify topology", domain="topology")
    run = await RunOrchestrator(registry, store).orchestrate(run_id)
    assert run.status == RunStatus.COMPLETED


async def test_orchestrate_produces_summary(store: JsonRunStore, registry: ExecutorRegistry):
    run_id = _create_run(store, description="verify topology", domain="topology")
    run = await RunOrchestrator(registry, store).orchestrate(run_id)
    assert run.summary is not None


async def test_orchestrate_produces_review(store: JsonRunStore, registry: ExecutorRegistry):
    run_id = _create_run(store, description="verify topology", domain="topology")
    run = await RunOrchestrator(registry, store).orchestrate(run_id)
    assert len(run.reviews) == 1
    assert run.reviews[0].verdict == ReviewVerdict.APPROVE


# --- Audit trail ---


async def test_steps_include_all_phases(store: JsonRunStore, registry: ExecutorRegistry):
    run_id = _create_run(store, description="verify", domain="topology")
    run = await RunOrchestrator(registry, store).orchestrate(run_id)

    kinds = [s.kind for s in run.steps]
    assert StepKind.DOMAIN_CALL in kinds
    assert StepKind.AI_SUMMARY in kinds
    assert StepKind.AI_REVIEW in kinds


async def test_domain_step_selection(store: JsonRunStore, registry: ExecutorRegistry):
    run_id = _create_run(store, description="verify", domain="topology")
    run = await RunOrchestrator(registry, store).orchestrate(run_id)

    domain_steps = [s for s in run.steps if s.kind == StepKind.DOMAIN_CALL]
    sel = domain_steps[0].selection
    assert sel.executor_id == "topo-exec"
    assert sel.reason == SelectionReason.DOMAIN_MATCH


async def test_ai_steps_use_general_fallback(store: JsonRunStore, registry: ExecutorRegistry):
    run_id = _create_run(store, description="verify", domain="topology")
    run = await RunOrchestrator(registry, store).orchestrate(run_id)

    ai_steps = [s for s in run.steps if s.kind in (StepKind.AI_SUMMARY, StepKind.AI_REVIEW)]
    for step in ai_steps:
        assert step.selection.executor_id == "ai-exec"
        assert step.selection.reason == SelectionReason.GENERAL_FALLBACK


async def test_steps_have_timestamps(store: JsonRunStore, registry: ExecutorRegistry):
    run_id = _create_run(store, description="verify", domain="topology")
    run = await RunOrchestrator(registry, store).orchestrate(run_id)
    for step in run.steps:
        assert step.started_at is not None
        assert step.finished_at is not None


# --- Feedback loop: review rejects, correction runs ---


async def test_feedback_loop_one_correction(store: JsonRunStore, tmp_path: Path):
    """Review rejects first time, approves after correction."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo-exec", domains=["topology"]))
    reg.register(
        MockExecutor(
            "ai-exec",
            review_verdicts=[ReviewVerdict.REQUEST_CHANGES, ReviewVerdict.APPROVE],
        )
    )

    s = JsonRunStore(tmp_path / "feedback_runs")
    run_id = _create_run(s, description="verify", domain="topology")
    run = await RunOrchestrator(reg, s).orchestrate(run_id)

    assert run.status == RunStatus.COMPLETED
    assert len(run.reviews) == 2
    assert run.reviews[0].verdict == ReviewVerdict.REQUEST_CHANGES
    assert run.reviews[1].verdict == ReviewVerdict.APPROVE

    correction_steps = [s for s in run.steps if s.kind == StepKind.CORRECTION]
    assert len(correction_steps) == 1
    assert correction_steps[0].iteration == 1


async def test_feedback_loop_max_retries(store: JsonRunStore, tmp_path: Path):
    """Review never approves — stops after max_corrections."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo-exec", domains=["topology"]))
    reg.register(
        MockExecutor(
            "ai-exec",
            review_verdicts=[ReviewVerdict.REJECT, ReviewVerdict.REJECT, ReviewVerdict.REJECT],
        )
    )

    s = JsonRunStore(tmp_path / "max_retry_runs")
    run_id = _create_run(s, description="verify", domain="topology")
    policy = BudgetPolicy(max_corrections=2)
    run = await RunOrchestrator(reg, s, policy=policy).orchestrate(run_id)

    assert run.status == RunStatus.COMPLETED
    # 3 reviews total: initial + 2 after corrections
    assert len(run.reviews) == 3
    assert all(r.verdict == ReviewVerdict.REJECT for r in run.reviews)

    completed_corrections = [
        s for s in run.steps if s.kind == StepKind.CORRECTION and s.status == StepStatus.COMPLETED
    ]
    assert len(completed_corrections) == 2


async def test_feedback_loop_iterations_tracked(store: JsonRunStore, tmp_path: Path):
    """Step iteration numbers increase through the feedback loop."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo-exec", domains=["topology"]))
    reg.register(
        MockExecutor(
            "ai-exec",
            review_verdicts=[ReviewVerdict.REQUEST_CHANGES, ReviewVerdict.APPROVE],
        )
    )

    s = JsonRunStore(tmp_path / "iter_runs")
    run_id = _create_run(s, description="verify", domain="topology")
    run = await RunOrchestrator(reg, s).orchestrate(run_id)

    review_steps = [s for s in run.steps if s.kind == StepKind.AI_REVIEW]
    assert review_steps[0].iteration == 0
    assert review_steps[1].iteration == 1

    correction_steps = [s for s in run.steps if s.kind == StepKind.CORRECTION]
    assert correction_steps[0].iteration == 1


async def test_no_correction_on_approve(store: JsonRunStore, registry: ExecutorRegistry):
    """When review approves, no correction step is created."""
    run_id = _create_run(store, description="verify", domain="topology")
    run = await RunOrchestrator(registry, store).orchestrate(run_id)

    correction_steps = [s for s in run.steps if s.kind == StepKind.CORRECTION]
    assert len(correction_steps) == 0
    assert len(run.reviews) == 1


# --- No AI executor ---


async def test_no_ai_executor_skips_all(store: JsonRunStore, tmp_path: Path):
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo-only", domains=["topology"]))
    s = JsonRunStore(tmp_path / "no_ai_runs")

    run_id = _create_run(s, description="verify", domain="topology")
    run = await RunOrchestrator(reg, s).orchestrate(run_id)

    assert run.summary is None
    assert len(run.reviews) == 0
    skipped = [s for s in run.steps if s.status == StepStatus.SKIPPED]
    assert len(skipped) >= 2


# --- Persistence ---


async def test_feedback_loop_persisted(store: JsonRunStore, tmp_path: Path):
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo-exec", domains=["topology"]))
    reg.register(
        MockExecutor(
            "ai-exec",
            review_verdicts=[ReviewVerdict.REQUEST_CHANGES, ReviewVerdict.APPROVE],
        )
    )

    s = JsonRunStore(tmp_path / "persist_runs")
    run_id = _create_run(s, description="verify", domain="topology")
    await RunOrchestrator(reg, s).orchestrate(run_id)

    from uuid import UUID

    loaded = s.get(UUID(run_id))
    assert len(loaded.reviews) == 2
    assert any(s.kind == StepKind.CORRECTION for s in loaded.steps)


# --- Health-aware executor selection ---


async def test_unhealthy_executor_skipped(store: JsonRunStore, tmp_path: Path):
    """An unhealthy domain executor is skipped; task falls back to general."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo-sick", domains=["topology"], healthy=False))
    reg.register(MockExecutor("ai-exec"))

    s = JsonRunStore(tmp_path / "health_runs")
    run_id = _create_run(s, description="verify", domain="topology")
    run = await RunOrchestrator(reg, s).orchestrate(run_id)

    assert run.status == RunStatus.COMPLETED
    # The unhealthy domain executor should not have been selected
    domain_steps = [st for st in run.steps if st.kind == StepKind.DOMAIN_CALL]
    for step in domain_steps:
        if step.selection and step.selection.executor_id:
            assert step.selection.executor_id != "topo-sick"


async def test_all_executors_unhealthy_skips_domain(store: JsonRunStore, tmp_path: Path):
    """When all executors are unhealthy, domain tasks are skipped."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo-sick", domains=["topology"], healthy=False))
    # No general-purpose executor either

    s = JsonRunStore(tmp_path / "all_sick_runs")
    run_id = _create_run(s, description="verify", domain="topology")
    run = await RunOrchestrator(reg, s).orchestrate(run_id)

    assert run.status == RunStatus.COMPLETED
    domain_steps = [st for st in run.steps if st.kind == StepKind.DOMAIN_CALL]
    assert all(st.status == StepStatus.SKIPPED for st in domain_steps)


async def test_healthy_executor_preferred_over_unhealthy(store: JsonRunStore, tmp_path: Path):
    """When both healthy and unhealthy domain executors exist, healthy is chosen."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo-sick", domains=["topology"], healthy=False))
    reg.register(MockExecutor("topo-ok", domains=["topology"], healthy=True))
    reg.register(MockExecutor("ai-exec"))

    s = JsonRunStore(tmp_path / "prefer_healthy_runs")
    run_id = _create_run(s, description="verify", domain="topology")
    run = await RunOrchestrator(reg, s).orchestrate(run_id)

    domain_steps = [st for st in run.steps if st.kind == StepKind.DOMAIN_CALL]
    for step in domain_steps:
        if step.selection and step.selection.executor_id:
            assert step.selection.executor_id == "topo-ok"


# --- Escalation ---


class FailingExecutor:
    """Executor that raises on execute/review after N successes."""

    def __init__(
        self,
        executor_id: str = "failing-exec",
        fail_after: int = 0,
    ) -> None:
        self._id = executor_id
        self._fail_after = fail_after
        self._call_count = 0
        self._capability = ExecutorCapability()

    @property
    def executor_id(self) -> str:
        return self._id

    @property
    def capability(self) -> ExecutorCapability:
        return self._capability

    async def execute(self, task):
        self._call_count += 1
        if self._call_count > self._fail_after:
            raise RuntimeError(f"executor crash #{self._call_count}")
        from vos.agentcore.taskkit.models import TaskOutcome, TaskStatus

        return TaskOutcome(
            status=TaskStatus.COMPLETED,
            result="ok",
            executor_id=self._id,
        )

    async def review(self, request):
        self._call_count += 1
        if self._call_count > self._fail_after:
            raise RuntimeError(f"review crash #{self._call_count}")
        from vos.agentcore.reviewkit.models import ReviewResult, ReviewVerdict

        return ReviewResult(
            request_id=request.review_id,
            verdict=ReviewVerdict.APPROVE,
            findings=[],
            summary="ok",
        )

    async def health(self):
        from vos.agentcore.executorkit.protocol import ExecutorHealth

        return ExecutorHealth(status="ok")


async def test_review_crash_continues_loop(store: JsonRunStore, tmp_path: Path):
    """Review failure doesn't kill the run — escalation allows retry."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo", domains=["topology"]))
    # Executor that crashes on first call (summary), so review uses MockExecutor
    # Actually: let's use a failing AI executor + a working fallback
    failing = FailingExecutor("ai-crash", fail_after=1)  # succeeds once (summary), then crashes
    reg.register(failing)
    reg.register(MockExecutor("ai-backup"))  # healthy backup

    s = JsonRunStore(tmp_path / "crash_runs")
    run_id = _create_run(s, description="verify", domain="topology")
    run = await RunOrchestrator(reg, s).orchestrate(run_id)

    # Run should still complete — crash didn't kill orchestration
    assert run.status == RunStatus.COMPLETED


async def test_escalation_tracks_failures(store: JsonRunStore, tmp_path: Path):
    """Executor failures are tracked and influence selection."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo", domains=["topology"]))

    # Single AI executor that crashes on first execute call
    failing = FailingExecutor("ai-only", fail_after=0)
    reg.register(failing)

    s = JsonRunStore(tmp_path / "escalation_runs")
    run_id = _create_run(s, description="verify", domain="topology")
    run = await RunOrchestrator(reg, s).orchestrate(run_id)

    # Run completes (doesn't raise)
    assert run.status == RunStatus.COMPLETED
    # Summary should have failed
    summary_steps = [st for st in run.steps if st.kind == StepKind.AI_SUMMARY]
    assert any(st.status == StepStatus.FAILED for st in summary_steps)


# --- Feedback loop resilience ---


async def test_review_failure_recorded_not_fatal(store: JsonRunStore, tmp_path: Path):
    """When review crashes, step is FAILED but run still completes."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo", domains=["topology"]))

    # Executor succeeds on execute (summary) but fails on review
    failing = FailingExecutor("ai-review-fail", fail_after=1)
    reg.register(failing)

    s = JsonRunStore(tmp_path / "resilient_runs")
    run_id = _create_run(s, description="verify", domain="topology")
    run = await RunOrchestrator(reg, s).orchestrate(run_id)

    assert run.status == RunStatus.COMPLETED
    review_steps = [st for st in run.steps if st.kind == StepKind.AI_REVIEW]
    assert any(st.status == StepStatus.FAILED for st in review_steps)


# --- Error paths ---


async def test_not_found(store: JsonRunStore, registry: ExecutorRegistry):
    with pytest.raises(OrchestrationError, match="not found"):
        await RunOrchestrator(registry, store).orchestrate(
            "00000000-0000-0000-0000-000000000000"
        )


async def test_no_plan(store: JsonRunStore, registry: ExecutorRegistry):
    run = RunRecord(status=RunStatus.CREATED)
    store.save(run)
    with pytest.raises(OrchestrationError, match="no plan"):
        await RunOrchestrator(registry, store).orchestrate(str(run.run_id))
