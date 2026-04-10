"""Tests for preflight verification tool via PreflightService."""

import pytest

from stitch.mcp.schemas import DetailLevel
from stitch.mcp.services.preflight_service import PreflightService


@pytest.mark.asyncio
async def test_preflight_no_adapters(engine):
    """Preflight with no adapters: 0 observations, everything missing."""
    svc = PreflightService(engine)
    resp = await svc.run(adapters=[])
    assert resp.ok
    data = resp.to_dict()
    assert "verdict" in data["result"]
    assert data["result"]["observations_collected"] == 0


@pytest.mark.asyncio
async def test_preflight_returns_findings(engine):
    svc = PreflightService(engine)
    resp = await svc.run(adapters=[], detail=DetailLevel.FULL)
    data = resp.to_dict()
    assert "findings" in data["result"]


@pytest.mark.asyncio
async def test_preflight_summary_mode(engine):
    svc = PreflightService(engine)
    resp = await svc.run(adapters=[], detail=DetailLevel.SUMMARY)
    data = resp.to_dict()
    assert data["result"]["findings"] == []
    assert "verdict" in data["result"]


@pytest.mark.asyncio
async def test_preflight_verdict_fail_when_missing(engine):
    """With no observations, all links should fail (devices missing)."""
    svc = PreflightService(engine)
    resp = await svc.run(adapters=[])
    data = resp.to_dict()
    assert data["result"]["verdict"] == "fail"


@pytest.mark.asyncio
async def test_preflight_counts(engine):
    """Summary counts should reflect the test topology."""
    svc = PreflightService(engine)
    resp = await svc.run(adapters=[])
    data = resp.to_dict()
    result = data["result"]
    assert result["links_total"] == 2
    assert result["links_fail"] >= 1
    assert "links_pass" in result
    assert "links_warning" in result


@pytest.mark.asyncio
async def test_preflight_topology_path_in_response(engine, topology_file):
    svc = PreflightService(engine)
    resp = await svc.run(adapters=[])
    data = resp.to_dict()
    assert data["meta"]["topology_path"] == topology_file
