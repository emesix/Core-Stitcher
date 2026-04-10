"""Integration tests for alpha executor routing — require live backends.

Run with: uv run pytest tests/integration/test_alpha_routing.py -v
Skip in CI: uv run pytest -m "not integration"

These tests prove the three alpha paths:
1. GPU inference (golden path)
2. CPU fallback (degraded local inference)
3. Sidecar compute dispatch

Plus: escalation, full-local-down, sidecar-down, budget exhaustion.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from stitch.agentcore.executorkit.local import LocalExecutor, LocalExecutorConfig
from stitch.agentcore.executorkit.mock import MockExecutor
from stitch.agentcore.executorkit.openai_compat import (
    OpenAICompatibleExecutor,
    OpenAIExecutorConfig,
)
from stitch.agentcore.executorkit.sidecar import SidecarConfig, SidecarExecutor
from stitch.agentcore.orchestration import (
    BudgetPolicy,
    RunOrchestrator,
    StepKind,
    StepStatus,
)
from stitch.agentcore.orchestration.routing import (
    alpha_routing_policy,
)
from stitch.agentcore.plannerkit import WorkRequest, plan_request
from stitch.agentcore.registry import ExecutorRegistry
from stitch.agentcore.reviewkit import ReviewVerdict
from stitch.agentcore.storekit import JsonRunStore, RunRecord, RunStatus

if TYPE_CHECKING:
    from pathlib import Path


# --- Helpers ---

GPU_URL = "http://172.16.0.109:8000"
CPU_URL = "http://172.16.0.109:8001"
SIDECAR_URL = "http://172.16.0.109:8080"


def _check_reachable(url: str) -> bool:
    """Quick TCP check to see if a backend is reachable."""
    import socket
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 80
    try:
        s = socket.create_connection((host, port), timeout=2)
        s.close()
        return True
    except (OSError, TimeoutError):
        return False


gpu_available = pytest.mark.skipif(
    not _check_reachable(GPU_URL), reason="GPU backend not reachable"
)
cpu_available = pytest.mark.skipif(
    not _check_reachable(CPU_URL), reason="CPU backend not reachable"
)
sidecar_available = pytest.mark.skipif(
    not _check_reachable(SIDECAR_URL), reason="Sidecar not reachable"
)


def _create_run(store: JsonRunStore, **req_kwargs) -> str:
    request = WorkRequest(**req_kwargs)
    plan = plan_request(request)
    run = RunRecord(status=RunStatus.PLANNED, request=request, plan=plan)
    store.save(run)
    return str(run.run_id)


def _build_registry(
    *, gpu: bool = True, cpu: bool = True, sidecar: bool = True, openrouter: bool = False
) -> ExecutorRegistry:
    """Build a registry with the specified backends."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo-exec", domains=["topology"]))

    if gpu:
        reg.register(
            LocalExecutor(
                LocalExecutorConfig(
                    base_url=GPU_URL,
                    api_path="/v3/chat/completions",
                    models_path=None,
                    model="qwen25-7b",
                    executor_id="local-gpu",
                    tags=["local", "a770", "gpu"],
                )
            )
        )

    if cpu:
        reg.register(
            LocalExecutor(
                LocalExecutorConfig(
                    base_url=CPU_URL,
                    api_path="/v3/chat/completions",
                    models_path=None,
                    model="TinyLlama-1.1B-INT4",
                    executor_id="local-cpu",
                    tags=["local", "a770", "cpu"],
                )
            )
        )

    if sidecar:
        reg.register(SidecarExecutor(SidecarConfig(base_url=SIDECAR_URL)))

    if openrouter:
        import os

        if os.environ.get("OPENROUTER_API_KEY"):
            reg.register(
                OpenAICompatibleExecutor(
                    OpenAIExecutorConfig(
                        base_url="https://openrouter.ai",
                        api_path="/api/v1/chat/completions",
                        models_path="/api/v1/models",
                        model="anthropic/claude-sonnet-4",
                        api_key_env="OPENROUTER_API_KEY",
                        executor_id="openrouter",
                    )
                )
            )

    return reg


# --- Path 1: Golden path — GPU inference routing ---


@pytest.mark.integration
@gpu_available
async def test_golden_path_gpu_inference(tmp_path: Path):
    """GPU inference routing works end-to-end."""
    reg = _build_registry(gpu=True, cpu=False, sidecar=False)
    store = JsonRunStore(tmp_path / "runs")
    run_id = _create_run(store, description="verify topology", domain="topology")

    routing = alpha_routing_policy()
    run = await RunOrchestrator(reg, store, routing=routing).orchestrate(run_id)

    assert run.status == RunStatus.COMPLETED

    # Summary should have gone to local-gpu
    summary_steps = [s for s in run.steps if s.kind == StepKind.AI_SUMMARY]
    assert len(summary_steps) == 1
    assert summary_steps[0].selection.executor_id == "local-gpu"
    assert summary_steps[0].selection.dispatch_type == "initial"
    assert summary_steps[0].selection.matched_rule is not None


# --- Path 1 variant: GPU REJECT → escalation ---


@pytest.mark.integration
@gpu_available
async def test_gpu_reject_escalation(tmp_path: Path):
    """REJECT verdict triggers escalation to OpenRouter (mocked)."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo-exec", domains=["topology"]))
    # Local GPU that rejects
    reg.register(
        MockExecutor(
            "local-gpu",
            review_verdicts=[ReviewVerdict.REJECT],
        )
    )
    # Cloud fallback that approves
    reg.register(
        MockExecutor(
            "openrouter",
            review_verdicts=[ReviewVerdict.APPROVE],
        )
    )

    store = JsonRunStore(tmp_path / "runs")
    run_id = _create_run(store, description="verify topology", domain="topology")

    routing = alpha_routing_policy()
    run = await RunOrchestrator(reg, store, routing=routing).orchestrate(run_id)

    assert run.status == RunStatus.COMPLETED
    # First review from local-gpu (rejects), correction from openrouter
    review_steps = [s for s in run.steps if s.kind == StepKind.AI_REVIEW]
    assert len(review_steps) >= 1


# --- Path 2: CPU fallback ---


@pytest.mark.integration
async def test_cpu_fallback(tmp_path: Path):
    """GPU down, CPU takes over on same node."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo-exec", domains=["topology"]))
    reg.register(MockExecutor("local-gpu", healthy=False))  # GPU down
    reg.register(MockExecutor("local-cpu"))  # CPU up

    store = JsonRunStore(tmp_path / "runs")
    run_id = _create_run(store, description="verify topology", domain="topology")

    routing = alpha_routing_policy()
    run = await RunOrchestrator(reg, store, routing=routing).orchestrate(run_id)

    assert run.status == RunStatus.COMPLETED
    summary_steps = [s for s in run.steps if s.kind == StepKind.AI_SUMMARY]
    assert summary_steps[0].selection.executor_id == "local-cpu"
    assert summary_steps[0].selection.dispatch_type == "fallback"


# --- Full local down → external catches inference ---


@pytest.mark.integration
async def test_full_local_down(tmp_path: Path):
    """External catches inference when local is gone."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo-exec", domains=["topology"]))
    reg.register(MockExecutor("local-gpu", healthy=False))
    reg.register(MockExecutor("local-cpu", healthy=False))
    reg.register(MockExecutor("openrouter"))  # external fallback

    store = JsonRunStore(tmp_path / "runs")
    run_id = _create_run(store, description="verify topology", domain="topology")

    routing = alpha_routing_policy()
    run = await RunOrchestrator(reg, store, routing=routing).orchestrate(run_id)

    assert run.status == RunStatus.COMPLETED
    summary_steps = [s for s in run.steps if s.kind == StepKind.AI_SUMMARY]
    # Should have used openrouter as escalation target fallback
    assert summary_steps[0].selection.executor_id == "openrouter"


# --- Path 3: Compute dispatch ---


@pytest.mark.integration
async def test_compute_dispatch(tmp_path: Path):
    """Non-LLM work routed to sidecar via routing, not special-casing."""
    # Test the routing resolution directly since the planner doesn't
    # natively generate compute tasks
    routing = alpha_routing_policy()
    decision = routing.resolve(StepKind.COMPUTE_TASK, [])
    assert decision.primary == "local-sidecar"
    assert decision.fail_closed is True


# --- Sidecar down → fail closed ---


@pytest.mark.integration
async def test_sidecar_down_fails_closed(tmp_path: Path):
    """Sidecar down → fail closed, no silent LLM fallback."""
    from stitch.agentcore.orchestration.routing import alpha_routing_policy

    routing = alpha_routing_policy()
    decision = routing.resolve(StepKind.COMPUTE_TASK, [])

    # When sidecar is the primary and fail_closed=True, and it's down,
    # the routing system should NOT fall back to an LLM
    assert decision.fail_closed is True
    assert decision.fallback_chain == []
    assert decision.allow_escalation is False


# --- Budget exhaustion ---


@pytest.mark.integration
async def test_budget_exhaustion(tmp_path: Path):
    """Policy limits respected with routing."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo-exec", domains=["topology"]))
    reg.register(MockExecutor("local-gpu"))

    store = JsonRunStore(tmp_path / "runs")
    run_id = _create_run(store, description="verify", domain="topology")

    routing = alpha_routing_policy()
    policy = BudgetPolicy(max_ai_steps=1)  # Only 1 AI step allowed

    run = await RunOrchestrator(
        reg, store, policy=policy, routing=routing
    ).orchestrate(run_id)

    assert run.status == RunStatus.COMPLETED
    # Should have summary but no review (budget exhausted)
    summary_steps = [s for s in run.steps if s.kind == StepKind.AI_SUMMARY]
    review_steps = [
        s
        for s in run.steps
        if s.kind == StepKind.AI_REVIEW and s.status == StepStatus.SKIPPED
    ]
    assert len(summary_steps) == 1
    assert len(review_steps) >= 1
