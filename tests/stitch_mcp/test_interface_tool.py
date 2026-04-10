"""Tests for the interface assign write-path tool."""

from unittest.mock import AsyncMock

import pytest

from stitch.mcp.services.interface_service import InterfaceService


@pytest.mark.asyncio
async def test_interface_assign_dry_run(engine):
    engine.gateway.call_tool = AsyncMock(
        return_value={
            "total": 3,
            "rows": [
                {"device": "igc0", "config": {"identifier": "wan"}, "description": "WAN"},
                {"device": "igc1", "config": {"identifier": "lan"}, "description": "LAN"},
                {"device": "ix0", "config": {}, "description": ""},
            ],
        }
    )
    svc = InterfaceService(engine)
    resp = await svc.assign("fw01", "ix0", "opt1", "Frontend", dry_run=True)
    assert resp.ok
    data = resp.to_dict()
    assert data["result"]["dry_run"] is True
    assert data["result"]["applied"] is False


@pytest.mark.asyncio
async def test_interface_assign_device_not_found(engine):
    svc = InterfaceService(engine)
    resp = await svc.assign("nonexistent", "ix0", "opt1", dry_run=True)
    assert not resp.ok
    assert resp.error["code"] == "DEVICE_NOT_FOUND"


@pytest.mark.asyncio
async def test_interface_assign_already_assigned(engine):
    engine.gateway.call_tool = AsyncMock(
        return_value={
            "total": 1,
            "rows": [
                {"device": "igc0", "config": {"identifier": "wan"}, "description": "WAN"},
            ],
        }
    )
    svc = InterfaceService(engine)
    resp = await svc.assign("fw01", "igc0", "opt1", dry_run=True)
    assert not resp.ok
    assert resp.error["code"] == "INTERFACE_ALREADY_ASSIGNED"


@pytest.mark.asyncio
async def test_interface_assign_interface_not_found(engine):
    engine.gateway.call_tool = AsyncMock(return_value={"total": 0, "rows": []})
    svc = InterfaceService(engine)
    resp = await svc.assign("fw01", "nonexistent", "opt1", dry_run=True)
    assert not resp.ok
    assert resp.error["code"] == "INTERFACE_NOT_FOUND"


@pytest.mark.asyncio
async def test_interface_assign_gateway_unavailable(engine):
    engine.gateway.call_tool = AsyncMock(side_effect=Exception("Connection refused"))
    svc = InterfaceService(engine)
    resp = await svc.assign("fw01", "ix0", "opt1", dry_run=True)
    assert not resp.ok
    assert resp.error["code"] == "GATEWAY_UNAVAILABLE"


@pytest.mark.asyncio
async def test_interface_assign_real_apply_not_implemented(engine):
    engine.gateway.call_tool = AsyncMock(
        return_value={
            "total": 1,
            "rows": [{"device": "ix0", "config": {}, "description": ""}],
        }
    )
    svc = InterfaceService(engine)
    resp = await svc.assign("fw01", "ix0", "opt1", dry_run=False)
    assert not resp.ok
    assert resp.error["code"] == "APPLY_FAILED"
    assert (
        "not yet implemented" in resp.error["message"].lower()
        or "v1" in resp.error["message"].lower()
    )


@pytest.mark.asyncio
async def test_interface_assign_gateway_returns_none(engine):
    """Gateway returns None (e.g. RPC error, empty content) — treat as unavailable."""
    engine.gateway.call_tool = AsyncMock(return_value=None)
    svc = InterfaceService(engine)
    resp = await svc.assign("fw01", "ix0", "opt1", dry_run=True)
    assert not resp.ok
    assert resp.error["code"] == "GATEWAY_UNAVAILABLE"
