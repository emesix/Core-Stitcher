"""Tests for TopologyExecutor — Ruggensgraat domain integration."""

from __future__ import annotations

from unittest.mock import patch

import httpx

from stitch.agentcore.executorkit import ExecutorProtocol
from stitch.agentcore.executorkit.topology import TopologyExecutor, TopologyExecutorConfig
from stitch.agentcore.registry import ExecutorRegistry
from stitch.agentcore.taskkit import TaskRecord, TaskStatus


def _config(**overrides) -> TopologyExecutorConfig:
    return TopologyExecutorConfig(base_url="http://fake:8000", **overrides)


def _patch_httpx(response_data: object, status_code: int = 200):
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
                json=response_data,
                request=httpx.Request("GET", url),
            )

        async def post(self, url: str, *, json=None, **kwargs):
            return httpx.Response(
                status_code,
                json=response_data,
                request=httpx.Request("POST", url),
            )

    return patch("httpx.AsyncClient", PatchedClient)


# --- Protocol compliance ---


def test_implements_protocol():
    assert isinstance(TopologyExecutor(_config()), ExecutorProtocol)


def test_executor_id():
    ex = TopologyExecutor(_config(executor_id="topo-1"))
    assert ex.executor_id == "topo-1"


def test_capability():
    ex = TopologyExecutor(_config())
    assert ex.capability.domains == ["topology"]
    assert "verify" in ex.capability.tags
    assert "diagnostics" in ex.capability.tags


# --- Health ---


async def test_health_ok():
    ex = TopologyExecutor(_config())
    with _patch_httpx({"meta": {"name": "test"}}):
        h = await ex.health()
    assert h.status == "ok"


async def test_health_error():
    class FailClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, **kwargs):
            raise httpx.ConnectError("refused")

    ex = TopologyExecutor(_config())
    with patch("httpx.AsyncClient", FailClient):
        h = await ex.health()
    assert h.status == "error"


# --- Execute: verify ---


async def test_execute_verify():
    report = {"results": [], "summary": {"total": 3, "pass": 3, "fail": 0}}
    ex = TopologyExecutor(_config())
    task = TaskRecord(
        description="verify topology",
        domain="topology",
        metadata={"action": "verify"},
    )
    with _patch_httpx(report):
        outcome = await ex.execute(task)
    assert outcome.status == TaskStatus.COMPLETED
    assert outcome.result["summary"]["total"] == 3


# --- Execute: trace ---


async def test_execute_trace():
    trace_result = {"vlan": 25, "status": "complete", "hops": []}
    ex = TopologyExecutor(_config())
    task = TaskRecord(
        description="trace vlan 25",
        domain="topology",
        metadata={"action": "trace", "params": {"vlan": 25, "source": "sw1"}},
    )
    with _patch_httpx(trace_result):
        outcome = await ex.execute(task)
    assert outcome.status == TaskStatus.COMPLETED
    assert outcome.result["vlan"] == 25


# --- Execute: diagnostics ---


async def test_execute_diagnostics():
    diag = {"total_devices": 3, "total_links": 2, "dangling_ports": []}
    ex = TopologyExecutor(_config())
    task = TaskRecord(
        description="run diagnostics",
        domain="topology",
        metadata={"action": "diagnostics"},
    )
    with _patch_httpx(diag):
        outcome = await ex.execute(task)
    assert outcome.status == TaskStatus.COMPLETED
    assert outcome.result["total_devices"] == 3


# --- Execute: device lookup ---


async def test_execute_device():
    device = {"name": "SW1", "type": "switch", "ports": {}}
    ex = TopologyExecutor(_config())
    task = TaskRecord(
        description="get device sw1",
        domain="topology",
        metadata={"action": "device", "params": {"device_id": "sw1"}},
    )
    with _patch_httpx(device):
        outcome = await ex.execute(task)
    assert outcome.status == TaskStatus.COMPLETED
    assert outcome.result["name"] == "SW1"


# --- Execute: unknown action ---


async def test_execute_unknown_action():
    ex = TopologyExecutor(_config())
    task = TaskRecord(
        description="unknown",
        domain="topology",
        metadata={"action": "nonexistent"},
    )
    outcome = await ex.execute(task)
    assert outcome.status == TaskStatus.FAILED
    assert "Unknown topology action" in outcome.error


# --- Execute: HTTP error ---


async def test_execute_http_error():
    class FailClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, **kwargs):
            raise httpx.ConnectError("refused")

    ex = TopologyExecutor(_config())
    task = TaskRecord(
        description="verify",
        domain="topology",
        metadata={"action": "verify"},
    )
    with patch("httpx.AsyncClient", FailClient):
        outcome = await ex.execute(task)
    assert outcome.status == TaskStatus.FAILED
    assert "refused" in outcome.error


# --- Execute: default action ---


async def test_execute_default_action():
    """No action in metadata defaults to 'verify'."""
    report = {"results": [], "summary": {}}
    ex = TopologyExecutor(_config())
    task = TaskRecord(description="check it", domain="topology")
    with _patch_httpx(report):
        outcome = await ex.execute(task)
    assert outcome.status == TaskStatus.COMPLETED


# --- Registry integration ---


def test_registry_resolves_topology():
    reg = ExecutorRegistry()
    reg.register(TopologyExecutor(_config()))
    task = TaskRecord(description="verify", domain="topology")
    matches = reg.find_for_task(task)
    assert len(matches) == 1
    assert matches[0].executor_id == "topology-ruggensgraat"


def test_registry_skips_for_other_domain():
    reg = ExecutorRegistry()
    reg.register(TopologyExecutor(_config()))
    task = TaskRecord(description="research", domain="research")
    matches = reg.find_for_task(task)
    assert matches == []


# --- Full pipeline: plan → resolve → execute ---


async def test_full_pipeline_topology():
    from stitch.agentcore.plannerkit import WorkRequest, plan_request

    reg = ExecutorRegistry()
    reg.register(TopologyExecutor(_config()))

    request = WorkRequest(description="verify topology", domain="topology")
    plan = plan_request(request)

    root = plan.root_task
    task = TaskRecord(
        description=root.description,
        domain=root.domain,
        metadata={"action": "verify"},
    )
    executors = reg.find_for_task(task)
    assert len(executors) == 1

    report = {"results": [], "summary": {"total": 3, "pass": 3}}
    with _patch_httpx(report):
        outcome = await executors[0].execute(task)
    assert outcome.status == TaskStatus.COMPLETED
    assert outcome.result["summary"]["pass"] == 3
