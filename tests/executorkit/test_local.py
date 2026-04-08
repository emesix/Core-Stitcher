"""Tests for LocalExecutor — discovery, health, availability, fallback."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import httpx

from vos.agentcore.executorkit import ExecutorProtocol
from vos.agentcore.executorkit.local import LocalExecutor, LocalExecutorConfig
from vos.agentcore.executorkit.mock import MockExecutor
from vos.agentcore.orchestration import BudgetPolicy, RunOrchestrator, StepKind
from vos.agentcore.plannerkit import WorkRequest, plan_request
from vos.agentcore.registry import ExecutorRegistry
from vos.agentcore.storekit import JsonRunStore, RunRecord, RunStatus
from vos.agentcore.taskkit import TaskRecord, TaskStatus

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
    from vos.agentcore.orchestration.budget import ExecutorTier

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
