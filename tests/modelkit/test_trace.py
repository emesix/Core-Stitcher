from __future__ import annotations

import pytest

from stitch.modelkit.enums import ObservationSource
from stitch.modelkit.trace import BreakPoint, TraceHop, TraceRequest, TraceResult


def test_trace_request_minimal():
    req = TraceRequest(vlan=10)
    assert req.vlan == 10
    assert req.source is None
    assert req.target is None


def test_trace_request_full():
    req = TraceRequest(vlan=20, source="switch-a", target="switch-b")
    assert req.source == "switch-a"
    assert req.target == "switch-b"


def test_trace_request_frozen():
    req = TraceRequest(vlan=10)
    with pytest.raises(Exception):
        req.vlan = 20  # type: ignore[misc]


def test_trace_hop_minimal():
    hop = TraceHop(status="ok", source=ObservationSource.MCP_LIVE)
    assert hop.status == "ok"
    assert hop.device is None
    assert hop.port is None
    assert hop.link is None
    assert hop.reason is None


def test_trace_hop_full():
    hop = TraceHop(
        device="switch-a",
        port="eth0",
        link="link-001",
        status="ok",
        source=ObservationSource.DECLARED,
        reason="vlan present",
    )
    assert hop.device == "switch-a"
    assert hop.reason == "vlan present"


def test_breakpoint_minimal():
    bp = BreakPoint(device="switch-a", port="eth0", reason="vlan not allowed", likely_causes=[])
    assert bp.device == "switch-a"
    assert bp.port == "eth0"
    assert bp.reason == "vlan not allowed"
    assert bp.likely_causes == []


def test_breakpoint_with_causes():
    bp = BreakPoint(
        device="switch-a",
        port="eth0",
        reason="vlan not allowed",
        likely_causes=["vlan not in trunk list", "port is access mode"],
    )
    assert len(bp.likely_causes) == 2


def test_breakpoint_frozen():
    bp = BreakPoint(device="switch-a", port="eth0", reason="test", likely_causes=[])
    with pytest.raises(Exception):
        bp.device = "switch-b"  # type: ignore[misc]


def test_trace_result_minimal():
    result = TraceResult(vlan=10, status="ok", hops=[])
    assert result.vlan == 10
    assert result.status == "ok"
    assert result.hops == []
    assert result.first_break is None
    assert result.source is None
    assert result.target is None


def test_trace_result_full():
    hop = TraceHop(status="ok", source=ObservationSource.MCP_LIVE)
    bp = BreakPoint(device="switch-a", port="eth0", reason="blocked", likely_causes=["acl"])
    result = TraceResult(
        vlan=10,
        source="switch-a",
        target="switch-b",
        status="broken",
        hops=[hop],
        first_break=bp,
    )
    assert result.source == "switch-a"
    assert result.first_break is not None
    assert len(result.hops) == 1
