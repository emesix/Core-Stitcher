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
                json={
                    "status": "ok",
                    "message": None,
                    "latency_ms": None,
                    "details": {"ovms_gpu0": "ok", "ovms_gpu1": "ok", "ovms_cpu": "ok"},
                },
                request=httpx.Request("GET", url),
            )

        async def post(self, url: str, *, json=None, **kwargs):
            resp = httpx.Response(
                exec_status,
                json={
                    "status": "completed",
                    "result": {"exit_code": 0, "stdout": "qwen25-7b", "stderr": ""},
                    "error": None,
                    "executor_id": "intell-a770",
                },
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
    assert "ovms_gpu0" in h.message


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
    assert outcome.result["status"] == "completed"
    assert outcome.result["result"]["exit_code"] == 0
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


def test_payload_includes_id_and_description():
    ex = SidecarExecutor(_config())
    task = TaskRecord(description="check models")
    payload = ex._build_payload(task)
    assert payload["id"] == str(task.id)
    assert payload["description"] == "check models"


def test_payload_includes_metadata():
    ex = SidecarExecutor(_config())
    task = TaskRecord(description="check", metadata={"host": "x"})
    payload = ex._build_payload(task)
    assert payload["metadata"] == {"host": "x"}


def test_payload_includes_domain():
    ex = SidecarExecutor(_config())
    task = TaskRecord(description="check", domain="topology")
    payload = ex._build_payload(task)
    assert payload["domain"] == "topology"


def test_payload_omits_empty_optional_fields():
    ex = SidecarExecutor(_config())
    task = TaskRecord(description="check")
    payload = ex._build_payload(task)
    assert "domain" not in payload
    assert "metadata" not in payload
