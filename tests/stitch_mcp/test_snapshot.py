"""Tests for snapshot capture, list, and diff."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from stitch.mcp.services.snapshot_service import SnapshotService


@pytest.fixture
def mock_engine(tmp_path, monkeypatch):
    """Engine with mocked gateway that returns sample data."""
    from stitch.mcp.engine import StitchEngine

    # Point snapshots to tmp dir
    monkeypatch.setattr("stitch.mcp.services.snapshot_service.SNAPSHOT_DIR", tmp_path)

    engine = AsyncMock(spec=StitchEngine)
    engine.gateway = AsyncMock()
    engine.gateway.call_tool = AsyncMock(side_effect=_mock_gateway_responses)
    return engine


def _mock_gateway_responses(tool_name: str, args: dict | None = None):
    """Return sample data for each captured tool."""
    responses = {
        "opnsense-get-interfaces": [
            {"device": "igc0", "status": "up", "config": {"identifier": "wan"}},
            {"device": "igc1", "status": "up", "config": {"identifier": "lan"}},
            {"device": "ix0", "status": "no carrier", "config": {}},
        ],
        "opnsense-firewall-get-rules": [
            {"uuid": "rule-1", "action": "pass", "interface": "wan", "source": "any"},
            {"uuid": "rule-2", "action": "block", "interface": "wan", "source": "private"},
        ],
        "opnsense-get-system-routes": [
            {"destination": "default", "gateway": "62.194.72.1", "interface": "igc0"},
            {"destination": "172.16.0.0/24", "gateway": "link#2", "interface": "igc1"},
        ],
        "opnsense-dhcp-get-leases": [
            {"address": "172.16.0.50", "hostname": "laptop", "mac": "aa:bb:cc:dd:ee:ff"},
        ],
        "opnsense-dhcp-list-static-mappings": [],
        "opnsense-get-system-status": {"uptime": "3 days", "version": "26.1.2"},
        "opnsense-get-system-health": {"cpu": 5, "memory": 42, "disk": 18},
    }
    return responses.get(tool_name, {})


@pytest.mark.asyncio
async def test_snapshot_capture(mock_engine, tmp_path, monkeypatch):
    monkeypatch.setattr("stitch.mcp.services.snapshot_service.SNAPSHOT_DIR", tmp_path)
    svc = SnapshotService(mock_engine)
    resp = await svc.capture(label="test")
    assert resp.ok
    data = resp.to_dict()
    assert data["result"]["section_count"] == 7
    assert data["result"]["failed"] == []
    assert "test" in data["result"]["file"]
    # Verify file was written
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1


@pytest.mark.asyncio
async def test_snapshot_capture_with_failures(mock_engine, tmp_path, monkeypatch):
    monkeypatch.setattr("stitch.mcp.services.snapshot_service.SNAPSHOT_DIR", tmp_path)
    # Make one tool fail
    async def failing_gateway(tool_name, args=None):
        if tool_name == "opnsense-get-system-health":
            raise ConnectionError("timeout")
        return _mock_gateway_responses(tool_name, args)

    mock_engine.gateway.call_tool = AsyncMock(side_effect=failing_gateway)
    svc = SnapshotService(mock_engine)
    resp = await svc.capture()
    assert resp.ok  # partial capture still succeeds
    data = resp.to_dict()
    assert "system_health" in data["result"]["failed"]
    assert data["result"]["section_count"] == 6


def test_snapshot_list(tmp_path, monkeypatch):
    monkeypatch.setattr("stitch.mcp.services.snapshot_service.SNAPSHOT_DIR", tmp_path)
    # Create some fake snapshots
    for i in range(3):
        (tmp_path / f"2026040{i}T120000Z.json").write_text(
            json.dumps(
                {
                    "timestamp": f"2026-04-0{i}",
                    "label": f"snap{i}",
                    "sections": {"a": 1},
                    "errors": [],
                }
            )
        )
    svc = SnapshotService(None)
    resp = svc.list_snapshots()
    assert resp.ok
    data = resp.to_dict()
    assert data["result"]["total"] == 3
    assert len(data["result"]["snapshots"]) == 3


def test_snapshot_list_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("stitch.mcp.services.snapshot_service.SNAPSHOT_DIR", tmp_path)
    svc = SnapshotService(None)
    resp = svc.list_snapshots()
    assert resp.ok
    assert resp.to_dict()["result"]["total"] == 0


def test_snapshot_diff(tmp_path, monkeypatch):
    monkeypatch.setattr("stitch.mcp.services.snapshot_service.SNAPSHOT_DIR", tmp_path)

    before = {
        "timestamp": "2026-04-10T10:00:00",
        "label": "before",
        "sections": {
            "interfaces": [
                {"device": "igc0", "config": {"identifier": "wan"}},
                {"device": "ix0", "config": {}},
            ],
            "firewall_rules": [
                {"uuid": "rule-1", "action": "pass"},
            ],
        },
        "errors": [],
    }
    after = {
        "timestamp": "2026-04-10T11:00:00",
        "label": "after",
        "sections": {
            "interfaces": [
                {"device": "igc0", "config": {"identifier": "wan"}},
                {"device": "ix0", "config": {"identifier": "opt1"}},  # changed!
            ],
            "firewall_rules": [
                {"uuid": "rule-1", "action": "pass"},
                {"uuid": "rule-3", "action": "pass"},  # added!
            ],
        },
        "errors": [],
    }

    (tmp_path / "before.json").write_text(json.dumps(before))
    (tmp_path / "after.json").write_text(json.dumps(after))

    svc = SnapshotService(None)
    resp = svc.diff("before.json", "after.json")
    assert resp.ok
    data = resp.to_dict()
    assert data["result"]["changed_sections"] == 2
    assert data["result"]["unchanged_sections"] == 0

    # Interface ix0 should show as modified
    iface_changes = data["result"]["changes"]["interfaces"]
    assert iface_changes["counts"]["modified"] == 1

    # Firewall rule-3 should show as added
    fw_changes = data["result"]["changes"]["firewall_rules"]
    assert fw_changes["counts"]["added"] == 1


def test_snapshot_diff_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("stitch.mcp.services.snapshot_service.SNAPSHOT_DIR", tmp_path)
    svc = SnapshotService(None)
    resp = svc.diff("nonexistent.json", "also-missing.json")
    assert not resp.ok
    assert "not found" in resp.error["message"].lower()


def test_snapshot_diff_section_added(tmp_path, monkeypatch):
    monkeypatch.setattr("stitch.mcp.services.snapshot_service.SNAPSHOT_DIR", tmp_path)

    before = {"timestamp": "t1", "sections": {"interfaces": []}, "errors": []}
    after = {
        "timestamp": "t2",
        "sections": {"interfaces": [], "system_health": {"cpu": 5}},
        "errors": [],
    }

    (tmp_path / "b.json").write_text(json.dumps(before))
    (tmp_path / "a.json").write_text(json.dumps(after))

    svc = SnapshotService(None)
    resp = svc.diff("b.json", "a.json")
    data = resp.to_dict()
    assert "system_health" in data["result"]["changes"]
    assert data["result"]["changes"]["system_health"]["change"] == "added"
