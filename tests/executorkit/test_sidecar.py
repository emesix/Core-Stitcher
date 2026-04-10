"""Tests for SidecarExecutor — health, execute, fail-closed behavior."""

from __future__ import annotations

from unittest.mock import patch

import httpx

from stitch.agentcore.executorkit import ExecutorProtocol
from stitch.agentcore.executorkit.sidecar import SidecarConfig, SidecarExecutor
from stitch.agentcore.taskkit.models import TaskRecord, TaskStatus


def _config(**overrides) -> SidecarConfig:
    return SidecarConfig(base_url="http://fake-sidecar:8080", **overrides)


def _patch_sidecar(health_status: int = 200, exec_status: int = 200):
    class PatchedClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url: str, **kwargs):
            return httpx.Response(
                health_status,
                json={"stage": "FULL", "status": "ok"},
                request=httpx.Request("GET", url),
            )

        async def post(self, url: str, *, json=None, **kwargs):
            resp = httpx.Response(
                exec_status,
                json={"result": "model_status", "models": ["Qwen2.5-7B"]},
                request=httpx.Request("POST", url),
            )
            if exec_status >= 400:
                resp.raise_for_status()
            return resp

    return patch("httpx.AsyncClient", PatchedClient)


def _patch_sidecar_down():
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
    assert isinstance(SidecarExecutor(_config()), ExecutorProtocol)


def test_executor_id():
    ex = SidecarExecutor(_config(executor_id="my-sidecar"))
    assert ex.executor_id == "my-sidecar"


def test_capability_tags():
    ex = SidecarExecutor(_config())
    assert "sidecar" in ex.capability.tags
    assert "compute" in ex.capability.tags
    assert ex.capability.domains == []


def test_no_review_method():
    """SidecarExecutor does NOT implement ReviewableExecutorProtocol."""
    from stitch.agentcore.executorkit.protocol import ReviewableExecutorProtocol

    ex = SidecarExecutor(_config())
    assert not isinstance(ex, ReviewableExecutorProtocol)


# --- Health ---


async def test_health_ok():
    ex = SidecarExecutor(_config())
    with _patch_sidecar():
        h = await ex.health()
    assert h.status == "ok"
    assert "FULL" in h.message


async def test_health_unreachable():
    ex = SidecarExecutor(_config())
    with _patch_sidecar_down():
        h = await ex.health()
    assert h.status == "error"
    assert "unreachable" in h.message


async def test_health_bad_status():
    ex = SidecarExecutor(_config())
    with _patch_sidecar(health_status=500):
        h = await ex.health()
    assert h.status == "error"
    assert "500" in h.message


# --- Execute ---


async def test_execute_success():
    ex = SidecarExecutor(_config())
    task = TaskRecord(description="check OVMS model status")

    with _patch_sidecar():
        outcome = await ex.execute(task)

    assert outcome.status == TaskStatus.COMPLETED
    assert outcome.result["result"] == "model_status"
    assert outcome.executor_id == "local-sidecar"
    assert outcome.started_at is not None
    assert outcome.finished_at is not None


async def test_execute_with_metadata():
    ex = SidecarExecutor(_config())
    task = TaskRecord(
        description="check ports",
        metadata={"host": "172.16.0.109"},
    )

    with _patch_sidecar():
        outcome = await ex.execute(task)
    assert outcome.status == TaskStatus.COMPLETED


async def test_execute_with_tags():
    ex = SidecarExecutor(_config())
    task = TaskRecord(description="check models", tags=["compute", "status"])

    with _patch_sidecar():
        outcome = await ex.execute(task)
    assert outcome.status == TaskStatus.COMPLETED


async def test_execute_when_down():
    """Execute fails when sidecar is unreachable — fail closed."""
    ex = SidecarExecutor(_config())
    task = TaskRecord(description="check models")

    with _patch_sidecar_down():
        outcome = await ex.execute(task)

    assert outcome.status == TaskStatus.FAILED
    assert "refused" in outcome.error


# --- Payload ---


def test_payload_includes_read_only():
    ex = SidecarExecutor(_config())
    task = TaskRecord(description="check models")
    payload = ex._build_payload(task)
    assert payload["read_only"] is True


def test_payload_includes_context():
    ex = SidecarExecutor(_config())
    task = TaskRecord(description="check", metadata={"host": "x"})
    payload = ex._build_payload(task)
    assert payload["context"] == {"host": "x"}


def test_payload_includes_tags():
    ex = SidecarExecutor(_config())
    task = TaskRecord(description="check", tags=["compute"])
    payload = ex._build_payload(task)
    assert payload["tags"] == ["compute"]
