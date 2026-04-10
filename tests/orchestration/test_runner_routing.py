"""Tests for RunOrchestrator with routing policy — routing-aware executor selection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from stitch.agentcore.executorkit.mock import MockExecutor
from stitch.agentcore.orchestration import (
    RoutingPolicy,
    RoutingRule,
    RunOrchestrator,
    StepKind,
    StepStatus,
)
from stitch.agentcore.orchestration.routing import EscalationTrigger
from stitch.agentcore.plannerkit import WorkRequest, plan_request
from stitch.agentcore.registry import ExecutorRegistry
from stitch.agentcore.reviewkit import ReviewVerdict
from stitch.agentcore.storekit import JsonRunStore, RunRecord, RunStatus

if TYPE_CHECKING:
    from pathlib import Path


def _create_run(store: JsonRunStore, **req_kwargs) -> str:
    request = WorkRequest(**req_kwargs)
    plan = plan_request(request)
    run = RunRecord(status=RunStatus.PLANNED, request=request, plan=plan)
    store.save(run)
    return str(run.run_id)


def _simple_routing() -> RoutingPolicy:
    """Routing policy: summary/review → local-gpu, correction → cloud."""
    return RoutingPolicy(
        rules=[
            RoutingRule(
                step_kinds=[StepKind.AI_SUMMARY, StepKind.AI_REVIEW],
                primary="local-gpu",
                fallback_chain=["cloud-ai"],
                escalation_target="cloud-ai",
                escalation_triggers=[EscalationTrigger.VERDICT_REJECT],
            ),
            RoutingRule(
                step_kinds=[StepKind.CORRECTION],
                primary="cloud-ai",
            ),
        ],
        default_primary="local-gpu",
        default_fallback="cloud-ai",
    )


# --- Routing-aware orchestration ---


async def test_routing_selects_primary(tmp_path: Path):
    """With routing policy, AI steps use the routed executor."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo", domains=["topology"]))
    reg.register(MockExecutor("local-gpu"))
    reg.register(MockExecutor("cloud-ai"))

    store = JsonRunStore(tmp_path / "runs")
    run_id = _create_run(store, description="verify", domain="topology")
    routing = _simple_routing()

    run = await RunOrchestrator(reg, store, routing=routing).orchestrate(run_id)

    assert run.status == RunStatus.COMPLETED
    summary_steps = [s for s in run.steps if s.kind == StepKind.AI_SUMMARY]
    assert summary_steps[0].selection.executor_id == "local-gpu"


async def test_routing_fallback_when_primary_down(tmp_path: Path):
    """When primary is unhealthy, fallback_chain is walked."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo", domains=["topology"]))
    reg.register(MockExecutor("local-gpu", healthy=False))
    reg.register(MockExecutor("cloud-ai"))

    store = JsonRunStore(tmp_path / "runs")
    run_id = _create_run(store, description="verify", domain="topology")
    routing = _simple_routing()

    run = await RunOrchestrator(reg, store, routing=routing).orchestrate(run_id)

    summary_steps = [s for s in run.steps if s.kind == StepKind.AI_SUMMARY]
    assert summary_steps[0].selection.executor_id == "cloud-ai"
    assert summary_steps[0].selection.dispatch_type == "fallback"


async def test_routing_metadata_persisted(tmp_path: Path):
    """Routing decision metadata is persisted in ExecutorSelection."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo", domains=["topology"]))
    reg.register(MockExecutor("local-gpu"))
    reg.register(MockExecutor("cloud-ai"))

    store = JsonRunStore(tmp_path / "runs")
    run_id = _create_run(store, description="verify", domain="topology")
    routing = _simple_routing()

    run = await RunOrchestrator(reg, store, routing=routing).orchestrate(run_id)

    summary_steps = [s for s in run.steps if s.kind == StepKind.AI_SUMMARY]
    sel = summary_steps[0].selection
    assert sel.matched_rule is not None
    assert sel.dispatch_type == "initial"
    assert sel.effective_tags is not None


async def test_routing_correction_uses_different_executor(tmp_path: Path):
    """Correction step uses a different executor per routing rules."""
    # summary/review → local-gpu, correction → cloud-ai
    routing = RoutingPolicy(
        rules=[
            RoutingRule(
                step_kinds=[StepKind.AI_SUMMARY, StepKind.AI_REVIEW],
                primary="local-gpu",
            ),
            RoutingRule(
                step_kinds=[StepKind.CORRECTION],
                primary="cloud-ai",
            ),
        ],
    )

    # Need local-gpu to reject on first review so correction triggers
    reg_corrected = ExecutorRegistry()
    reg_corrected.register(MockExecutor("topo", domains=["topology"]))
    reg_corrected.register(
        MockExecutor(
            "local-gpu",
            review_verdicts=[ReviewVerdict.REQUEST_CHANGES, ReviewVerdict.APPROVE],
        )
    )
    reg_corrected.register(MockExecutor("cloud-ai"))

    store2 = JsonRunStore(tmp_path / "runs2")
    run_id2 = _create_run(store2, description="verify", domain="topology")

    run = await RunOrchestrator(
        reg_corrected, store2, routing=routing
    ).orchestrate(run_id2)

    correction_steps = [s for s in run.steps if s.kind == StepKind.CORRECTION]
    assert len(correction_steps) == 1
    assert correction_steps[0].selection.executor_id == "cloud-ai"


# --- Fail-closed behavior ---


async def test_fail_closed_blocks_execution(tmp_path: Path):
    """Fail-closed rule prevents execution when primary and fallbacks are down."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo", domains=["topology"]))
    # No local-gpu or cloud executor registered

    store = JsonRunStore(tmp_path / "runs")
    run_id = _create_run(
        store, description="verify", domain="topology", tags=["high_risk"]
    )

    routing = RoutingPolicy(
        rules=[
            RoutingRule(
                tags=["high_risk"],
                primary="openrouter",
                fail_closed=True,
            ),
        ],
    )

    run = await RunOrchestrator(reg, store, routing=routing).orchestrate(run_id)

    # Summary should be skipped (fail-closed, openrouter not registered)
    summary_steps = [s for s in run.steps if s.kind == StepKind.AI_SUMMARY]
    assert summary_steps[0].status == StepStatus.SKIPPED
    assert summary_steps[0].selection.dispatch_type == "fail_closed"

    # Review should also be skipped — and only ONCE (early break, not max_reviews times)
    review_steps = [s for s in run.steps if s.kind == StepKind.AI_REVIEW]
    assert len(review_steps) == 1
    assert review_steps[0].status == StepStatus.SKIPPED
    assert review_steps[0].selection.dispatch_type == "fail_closed"


# --- Tags propagation ---


async def test_run_tags_propagated(tmp_path: Path):
    """Run-level tags are propagated to routing decisions."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo", domains=["topology"]))
    reg.register(MockExecutor("openrouter"))

    store = JsonRunStore(tmp_path / "runs")
    run_id = _create_run(
        store, description="verify", domain="topology", tags=["write_path"]
    )

    routing = RoutingPolicy(
        rules=[
            RoutingRule(
                tags=["write_path"],
                primary="openrouter",
                fail_closed=True,
            ),
        ],
    )

    run = await RunOrchestrator(reg, store, routing=routing).orchestrate(run_id)

    summary_steps = [s for s in run.steps if s.kind == StepKind.AI_SUMMARY]
    assert summary_steps[0].selection.executor_id == "openrouter"
    assert "write_path" in summary_steps[0].selection.effective_tags


# --- Escalation ---


async def test_reject_triggers_escalated_review(tmp_path: Path):
    """REJECT verdict triggers escalation: re-review with escalation target."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo", domains=["topology"]))
    # local-gpu rejects on review
    reg.register(MockExecutor("local-gpu", review_verdicts=[ReviewVerdict.REJECT]))
    # cloud-ai (escalation target) approves
    reg.register(MockExecutor("cloud-ai", review_verdicts=[ReviewVerdict.APPROVE]))

    store = JsonRunStore(tmp_path / "runs")
    run_id = _create_run(store, description="verify", domain="topology")
    routing = _simple_routing()

    run = await RunOrchestrator(reg, store, routing=routing).orchestrate(run_id)

    assert run.status == RunStatus.COMPLETED
    review_steps = [s for s in run.steps if s.kind == StepKind.AI_REVIEW]
    # First review: local-gpu REJECT, second review: cloud-ai APPROVE (escalated)
    assert len(review_steps) >= 2
    assert review_steps[0].selection.executor_id == "local-gpu"
    assert review_steps[1].selection.executor_id == "cloud-ai"
    assert review_steps[1].selection.dispatch_type == "escalated"
    assert "escalated" in review_steps[1].description


async def test_escalation_skipped_when_not_configured(tmp_path: Path):
    """No escalation when routing rule has allow_escalation=False."""
    routing = RoutingPolicy(
        rules=[
            RoutingRule(
                step_kinds=[StepKind.AI_SUMMARY, StepKind.AI_REVIEW],
                primary="local-gpu",
                allow_escalation=False,  # no escalation
            ),
            RoutingRule(
                step_kinds=[StepKind.CORRECTION],
                primary="cloud-ai",
            ),
        ],
    )

    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo", domains=["topology"]))
    reg.register(
        MockExecutor(
            "local-gpu",
            review_verdicts=[ReviewVerdict.REQUEST_CHANGES, ReviewVerdict.APPROVE],
        )
    )
    reg.register(MockExecutor("cloud-ai"))

    store = JsonRunStore(tmp_path / "runs")
    run_id = _create_run(store, description="verify", domain="topology")

    run = await RunOrchestrator(reg, store, routing=routing).orchestrate(run_id)

    # Should go straight to correction, no escalated review
    review_steps = [s for s in run.steps if s.kind == StepKind.AI_REVIEW]
    for step in review_steps:
        assert step.selection.executor_id == "local-gpu"


# --- No routing policy = legacy behavior ---


async def test_no_routing_uses_legacy(tmp_path: Path):
    """Without routing policy, legacy _find_ai_executor() behavior preserved."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo", domains=["topology"]))
    reg.register(MockExecutor("ai-exec"))

    store = JsonRunStore(tmp_path / "runs")
    run_id = _create_run(store, description="verify", domain="topology")

    # No routing policy
    run = await RunOrchestrator(reg, store).orchestrate(run_id)

    assert run.status == RunStatus.COMPLETED
    summary_steps = [s for s in run.steps if s.kind == StepKind.AI_SUMMARY]
    assert summary_steps[0].selection.executor_id == "ai-exec"
