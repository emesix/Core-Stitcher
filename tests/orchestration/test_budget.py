"""Tests for budget policy — spending limits, escalation, and gated AI steps."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from stitch.agentcore.executorkit.mock import MockExecutor
from stitch.agentcore.orchestration import BudgetPolicy, RunOrchestrator, StepKind, StepStatus
from stitch.agentcore.orchestration.budget import EscalationAction
from stitch.agentcore.plannerkit import WorkRequest, plan_request
from stitch.agentcore.registry import ExecutorRegistry
from stitch.agentcore.reviewkit import ReviewVerdict
from stitch.agentcore.storekit import JsonRunStore, RunRecord, RunStatus
from stitch.agentcore.storekit.models import SelectionReason

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def store(tmp_path: Path) -> JsonRunStore:
    return JsonRunStore(tmp_path / "runs")


def _reg(
    ai_verdicts: list[ReviewVerdict] | None = None,
) -> ExecutorRegistry:
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo", domains=["topology"]))
    reg.register(MockExecutor("ai", review_verdicts=ai_verdicts or [ReviewVerdict.APPROVE]))
    return reg


def _create_run(store: JsonRunStore, **kw) -> str:
    req = WorkRequest(**kw)
    plan = plan_request(req)
    run = RunRecord(status=RunStatus.PLANNED, request=req, plan=plan)
    store.save(run)
    return str(run.run_id)


# --- BudgetPolicy unit tests ---


def test_default_policy():
    p = BudgetPolicy()
    assert p.max_ai_steps == 10
    assert p.max_corrections == 2
    assert p.allow_ai_summary is True
    assert p.allow_ai_review is True


def test_can_run_ai_step():
    p = BudgetPolicy(max_ai_steps=3)
    assert p.can_run_ai_step(0) is True
    assert p.can_run_ai_step(2) is True
    assert p.can_run_ai_step(3) is False


def test_can_correct():
    p = BudgetPolicy(max_corrections=1)
    assert p.can_correct(0) is True
    assert p.can_correct(1) is False


def test_can_review():
    p = BudgetPolicy(max_reviews=2)
    assert p.can_review(0) is True
    assert p.can_review(2) is False


def test_escalation_decisions():
    p = BudgetPolicy()
    assert p.should_escalate(0) == EscalationAction.REUSE
    assert p.should_escalate(1) == EscalationAction.SWITCH
    assert p.should_escalate(2) == EscalationAction.STOP


# --- Budget-gated orchestration ---


async def test_ai_summary_disabled(store: JsonRunStore):
    policy = BudgetPolicy(allow_ai_summary=False)
    reg = _reg()
    run_id = _create_run(store, description="verify", domain="topology")
    run = await RunOrchestrator(reg, store, policy=policy).orchestrate(run_id)

    assert run.summary is None
    # No summary step at all (not even skipped — policy prevents entry)
    summary_steps = [s for s in run.steps if s.kind == StepKind.AI_SUMMARY]
    assert len(summary_steps) == 0


async def test_ai_review_disabled(store: JsonRunStore):
    policy = BudgetPolicy(allow_ai_review=False)
    reg = _reg()
    run_id = _create_run(store, description="verify", domain="topology")
    run = await RunOrchestrator(reg, store, policy=policy).orchestrate(run_id)

    assert len(run.reviews) == 0
    review_steps = [s for s in run.steps if s.kind == StepKind.AI_REVIEW]
    assert len(review_steps) == 0


async def test_max_ai_steps_limits_total(store: JsonRunStore):
    """With max_ai_steps=2, only summary + 1 review can run (no correction)."""
    policy = BudgetPolicy(max_ai_steps=2)
    reg = _reg(ai_verdicts=[ReviewVerdict.REQUEST_CHANGES, ReviewVerdict.APPROVE])
    run_id = _create_run(store, description="verify", domain="topology")
    run = await RunOrchestrator(reg, store, policy=policy).orchestrate(run_id)

    # Budget: summary (1) + review (2) = 2 steps, no room for correction
    ai_completed = [
        s
        for s in run.steps
        if s.kind in (StepKind.AI_SUMMARY, StepKind.AI_REVIEW, StepKind.CORRECTION)
        and s.status == StepStatus.COMPLETED
    ]
    assert len(ai_completed) == 2

    budget_skipped = [
        s
        for s in run.steps
        if s.selection and s.selection.reason == SelectionReason.BUDGET_EXHAUSTED
    ]
    assert len(budget_skipped) >= 1


async def test_max_ai_steps_one_allows_only_summary(store: JsonRunStore):
    """With max_ai_steps=1, only summary runs, review is budget-skipped."""
    policy = BudgetPolicy(max_ai_steps=1)
    reg = _reg()
    run_id = _create_run(store, description="verify", domain="topology")
    run = await RunOrchestrator(reg, store, policy=policy).orchestrate(run_id)

    assert run.summary is not None
    assert len(run.reviews) == 0

    skipped = [
        s
        for s in run.steps
        if s.selection and s.selection.reason == SelectionReason.BUDGET_EXHAUSTED
    ]
    assert len(skipped) >= 1


async def test_max_corrections_zero(store: JsonRunStore):
    """With max_corrections=0, review runs but no correction even on reject."""
    policy = BudgetPolicy(max_corrections=0)
    reg = _reg(ai_verdicts=[ReviewVerdict.REQUEST_CHANGES])
    run_id = _create_run(store, description="verify", domain="topology")
    run = await RunOrchestrator(reg, store, policy=policy).orchestrate(run_id)

    assert len(run.reviews) == 1
    assert run.reviews[0].verdict == ReviewVerdict.REQUEST_CHANGES

    correction_steps = [s for s in run.steps if s.kind == StepKind.CORRECTION]
    # Correction was skipped by policy
    skipped = [s for s in correction_steps if s.status == StepStatus.SKIPPED]
    assert len(skipped) == 1


async def test_full_budget_run(store: JsonRunStore):
    """Default policy allows full feedback loop."""
    reg = _reg(ai_verdicts=[ReviewVerdict.REQUEST_CHANGES, ReviewVerdict.APPROVE])
    run_id = _create_run(store, description="verify", domain="topology")
    run = await RunOrchestrator(reg, store).orchestrate(run_id)

    assert run.status == RunStatus.COMPLETED
    assert len(run.reviews) == 2
    assert run.reviews[-1].verdict == ReviewVerdict.APPROVE

    # No budget-skipped steps
    budget_skipped = [
        s
        for s in run.steps
        if s.selection and s.selection.reason == SelectionReason.BUDGET_EXHAUSTED
    ]
    assert len(budget_skipped) == 0


# --- Budget persistence ---


async def test_budget_decisions_persisted(store: JsonRunStore):
    policy = BudgetPolicy(max_ai_steps=1)
    reg = _reg()
    run_id = _create_run(store, description="verify", domain="topology")
    await RunOrchestrator(reg, store, policy=policy).orchestrate(run_id)

    from uuid import UUID

    loaded = store.get(UUID(run_id))
    skipped = [
        s
        for s in loaded.steps
        if s.selection and s.selection.reason == SelectionReason.BUDGET_EXHAUSTED
    ]
    assert len(skipped) >= 1
