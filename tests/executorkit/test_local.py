"""Tests for LocalExecutor — discovery, health, availability, fallback."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import patch

import httpx

from stitch.agentcore.executorkit import ExecutorProtocol
from stitch.agentcore.executorkit.local import LocalExecutor, LocalExecutorConfig
from stitch.agentcore.executorkit.mock import MockExecutor
from stitch.agentcore.orchestration import BudgetPolicy, RunOrchestrator, StepKind
from stitch.agentcore.plannerkit import WorkRequest, plan_request
from stitch.agentcore.registry import ExecutorRegistry
from stitch.agentcore.storekit import JsonRunStore, RunRecord, RunStatus
from stitch.agentcore.taskkit import TaskRecord, TaskStatus

if TYPE_CHECKING:
    from pathlib import Path


def _config(**overrides) -> LocalExecutorConfig:
    return LocalExecutorConfig(base_url="http://fake-local:11434/v1", **overrides)


def _patch_local(status_code: int = 200):
    class PatchedClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url: str, **kwargs):
            return httpx.Response(
                status_code,
                json={"data": [{"id": "llama3.2"}]},
                request=httpx.Request("GET", url),
            )

        async def post(self, url: str, *, headers=None, json=None, **kwargs):
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "local result"}}],
                    "model": "llama3.2",
                },
                request=httpx.Request("POST", url),
            )

    return patch("httpx.AsyncClient", PatchedClient)


def _patch_local_down():
    class FailClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, **kwargs):
            raise httpx.ConnectError("connection refused")

        async def post(self, url, **kwargs):
            raise httpx.ConnectError("connection refused")

    return patch("httpx.AsyncClient", FailClient)


# --- Protocol ---


def test_implements_protocol():
    assert isinstance(LocalExecutor(_config()), ExecutorProtocol)


def test_executor_id():
    ex = LocalExecutor(_config(executor_id="my-a770"))
    assert ex.executor_id == "my-a770"


def test_capability_tags():
    ex = LocalExecutor(_config())
    assert "local" in ex.capability.tags
    assert "a770" in ex.capability.tags
    assert ex.capability.domains == []


def test_tier():
    from stitch.agentcore.orchestration.budget import ExecutorTier

    ex = LocalExecutor(_config())
    assert ex.tier == ExecutorTier.LOCAL


# --- Health ---


async def test_health_ok():
    ex = LocalExecutor(_config())
    with _patch_local():
        h = await ex.health()
    assert h.status == "ok"
    assert ex.available is True


async def test_health_unreachable():
    ex = LocalExecutor(_config())
    with _patch_local_down():
        h = await ex.health()
    assert h.status == "error"
    assert ex.available is False


# --- Execute ---


async def test_execute_when_available():
    ex = LocalExecutor(_config())
    ex._available = True
    task = TaskRecord(description="test")
    with _patch_local():
        outcome = await ex.execute(task)
    assert outcome.status == TaskStatus.COMPLETED
    assert outcome.result == "local result"


async def test_execute_when_unavailable():
    ex = LocalExecutor(_config())
    ex._available = False
    task = TaskRecord(description="test")
    outcome = await ex.execute(task)
    assert outcome.status == TaskStatus.FAILED
    assert "unavailable" in outcome.error


# --- Registry + prefer_local ---


def _create_run(store: JsonRunStore, **kw) -> str:
    req = WorkRequest(**kw)
    plan = plan_request(req)
    run = RunRecord(status=RunStatus.PLANNED, request=req, plan=plan)
    store.save(run)
    return str(run.run_id)


async def test_prefer_local_selects_local(tmp_path: Path):
    """When prefer_local=True and local is available, local is chosen for AI steps."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo", domains=["topology"]))
    reg.register(MockExecutor("cloud-ai"))  # general, not local

    local = LocalExecutor(_config(executor_id="local-ai"))
    local._available = True
    reg.register(local)

    store = JsonRunStore(tmp_path / "runs")
    policy = BudgetPolicy(prefer_local=True)
    run_id = _create_run(store, description="verify", domain="topology")

    with _patch_local():
        run = await RunOrchestrator(reg, store, policy=policy).orchestrate(run_id)

    summary_steps = [s for s in run.steps if s.kind == StepKind.AI_SUMMARY]
    assert summary_steps[0].selection.executor_id == "local-ai"


async def test_fallback_to_cloud_when_local_unavailable(tmp_path: Path):
    """When local is down, falls back to cloud executor."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo", domains=["topology"]))
    reg.register(MockExecutor("cloud-ai"))

    local = LocalExecutor(_config(executor_id="local-ai"))
    local._available = False  # marked down
    reg.register(local)

    store = JsonRunStore(tmp_path / "runs")
    policy = BudgetPolicy(prefer_local=True)
    run_id = _create_run(store, description="verify", domain="topology")

    run = await RunOrchestrator(reg, store, policy=policy).orchestrate(run_id)

    summary_steps = [s for s in run.steps if s.kind == StepKind.AI_SUMMARY]
    # Should have fallen back to cloud-ai since local is unavailable
    assert summary_steps[0].selection.executor_id == "cloud-ai"


async def test_no_prefer_local_uses_first_available(tmp_path: Path):
    """Without prefer_local, first general executor is used (registration order)."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo", domains=["topology"]))
    reg.register(MockExecutor("cloud-ai"))  # registered first

    local = LocalExecutor(_config(executor_id="local-ai"))
    local._available = True
    reg.register(local)

    store = JsonRunStore(tmp_path / "runs")
    policy = BudgetPolicy(prefer_local=False)
    run_id = _create_run(store, description="verify", domain="topology")

    with _patch_local():
        run = await RunOrchestrator(reg, store, policy=policy).orchestrate(run_id)

    summary_steps = [s for s in run.steps if s.kind == StepKind.AI_SUMMARY]
    assert summary_steps[0].selection.executor_id == "cloud-ai"


# --- Health staleness and auto-recovery ---


async def test_health_reports_loaded_models():
    """Health check parses model list from /models response."""
    ex = LocalExecutor(_config())
    with _patch_local():
        h = await ex.health()
    assert h.status == "ok"
    assert "llama3.2" in ex.loaded_models


async def test_health_reports_latency():
    """Health check includes latency measurement."""
    ex = LocalExecutor(_config())
    with _patch_local():
        h = await ex.health()
    # Latency may be None in test (mocked response) but field exists
    assert hasattr(h, "latency_ms")


async def test_health_staleness_triggers_recheck():
    """When health TTL expires, execute re-checks before failing."""
    ex = LocalExecutor(_config(health_ttl=0.0))  # immediately stale
    # Mark as unavailable with an old timestamp
    ex._available = False
    ex._last_check = datetime(2020, 1, 1, tzinfo=UTC)

    task = TaskRecord(description="test")
    with _patch_local():
        outcome = await ex.execute(task)
    # Should have re-checked health, found endpoint up, and executed
    assert outcome.status == TaskStatus.COMPLETED
    assert ex.available is True


async def test_no_recheck_when_health_fresh():
    """When health TTL hasn't expired, execute fails fast without re-checking."""
    ex = LocalExecutor(_config(health_ttl=9999.0))
    ex._available = False
    ex._last_check = datetime.now(UTC)  # fresh

    task = TaskRecord(description="test")
    outcome = await ex.execute(task)
    assert outcome.status == TaskStatus.FAILED
    assert "unavailable" in outcome.error


# --- Review availability ---


async def test_review_when_unavailable():
    """Review returns REQUEST_CHANGES when local executor is down."""
    from stitch.agentcore.reviewkit.models import ReviewRequest, ReviewVerdict

    ex = LocalExecutor(_config(health_ttl=9999.0))
    ex._available = False
    ex._last_check = datetime.now(UTC)

    request = ReviewRequest(content={"test": True}, criteria=["quality"])
    result = await ex.review(request)
    assert result.verdict == ReviewVerdict.REQUEST_CHANGES
    assert any("unavailable" in f.description.lower() for f in result.findings)


async def test_review_when_available():
    """Review works normally when executor is up."""
    from stitch.agentcore.reviewkit.models import ReviewRequest, ReviewVerdict

    ex = LocalExecutor(_config())
    ex._available = True

    request = ReviewRequest(content={"test": True}, criteria=["quality"])
    with _patch_local():
        result = await ex.review(request)
    assert result.verdict == ReviewVerdict.APPROVE


# --- Env var override ---


async def test_env_var_overrides_base_url(monkeypatch):
    """LOCAL_EXECUTOR_URL env var overrides config base_url."""
    monkeypatch.setenv("LOCAL_EXECUTOR_URL", "http://custom-host:9999/v1")
    ex = LocalExecutor(_config())
    assert ex._effective_url == "http://custom-host:9999/v1"
