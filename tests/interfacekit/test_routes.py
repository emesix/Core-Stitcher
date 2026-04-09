"""Tests for interfacekit routes — HTTP API over PreflightWorkflowProtocol.

Uses FastAPI TestClient with a real PreflightWorkflow backed by a FakeCollector,
proving the full HTTP path: request → interfacekit → workflow → report → response.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stitch.apps.preflight import PreflightWorkflow
from stitch.interfacekit.routes import create_preflight_router
from stitch.modelkit.enums import ObservationSource
from stitch.modelkit.observation import Observation

TOPO_FIXTURE = Path(__file__).parent.parent / "fixtures" / "topology_sample.json"


class FakeCollector:
    def __init__(self, observations: list[Observation]) -> None:
        self._observations = observations

    async def collect(self) -> list[Observation]:
        return self._observations


def _matching_observations() -> list[Observation]:
    """Observations that match the sample topology fixture."""
    obs: list[Observation] = []
    devices = [("onti-be", "switch"), ("opnsense", "firewall"), ("pve-hx310-db", "proxmox")]
    for device, dtype in devices:
        obs.append(
            Observation(
                device=device,
                field="type",
                value=dtype,
                source=ObservationSource.MCP_LIVE,
                adapter="fake",
            )
        )

    ports = [
        ("onti-be", "eth1", "sfp+"),
        ("onti-be", "eth2", "sfp+"),
        ("opnsense", "ix1", "sfp+"),
        ("pve-hx310-db", "enp2s0", "sfp+"),
        ("pve-hx310-db", "vmbr0", "bridge"),
    ]
    for device, port, ptype in ports:
        obs.append(
            Observation(
                device=device,
                port=port,
                field="type",
                value=ptype,
                source=ObservationSource.MCP_LIVE,
                adapter="fake",
            )
        )

    return obs


@pytest.fixture
def client() -> TestClient:
    workflow = PreflightWorkflow(TOPO_FIXTURE, collectors=[FakeCollector(_matching_observations())])
    router = create_preflight_router(workflow)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_verify_returns_report(client: TestClient):
    resp = client.post("/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "summary" in data
    assert data["summary"]["total"] == 3


def test_verify_report_structure(client: TestClient):
    resp = client.post("/verify")
    data = resp.json()
    for result in data["results"]:
        assert "link" in result
        assert "link_type" in result
        assert "status" in result
        assert "checks" in result
        assert isinstance(result["checks"], list)


def test_verify_all_pass(client: TestClient):
    resp = client.post("/verify")
    data = resp.json()
    assert data["summary"]["pass"] == 3
    assert data["summary"]["fail"] == 0


def test_topology_endpoint(client: TestClient):
    resp = client.get("/topology")
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["name"] == "homelab-sample"
    assert len(data["devices"]) == 3
    assert len(data["links"]) == 3


def test_verify_with_missing_device():
    """Empty collector → all links fail."""
    workflow = PreflightWorkflow(TOPO_FIXTURE, collectors=[FakeCollector([])])
    router = create_preflight_router(workflow)
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)

    resp = c.post("/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["fail"] == 3


# --- Impact endpoint ---


def test_impact_returns_result(client: TestClient):
    resp = client.post(
        "/impact",
        json={
            "action": "remove_link",
            "device": "onti-be",
            "parameters": {"link_id": "phys-opnsense-ix1-to-onti-be-eth1"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "proposed_change" in data
    assert "impact" in data
    assert "risk" in data
    assert "safe_to_apply" in data


def test_impact_result_has_effects(client: TestClient):
    resp = client.post(
        "/impact",
        json={
            "action": "remove_link",
            "device": "onti-be",
            "parameters": {"link_id": "phys-opnsense-ix1-to-onti-be-eth1"},
        },
    )
    data = resp.json()
    assert len(data["impact"]) > 0
    for effect in data["impact"]:
        assert "device" in effect
        assert "effect" in effect
        assert "severity" in effect


def test_impact_nonexistent_link(client: TestClient):
    resp = client.post(
        "/impact",
        json={
            "action": "remove_link",
            "device": "onti-be",
            "parameters": {"link_id": "nonexistent"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["impact"]) == 0
    assert data["safe_to_apply"] is True


def test_impact_remove_vlan(client: TestClient):
    resp = client.post(
        "/impact",
        json={
            "action": "remove_vlan",
            "device": "onti-be",
            "port": "eth1",
            "parameters": {"vlan_id": 25},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "impact" in data


# --- Trace endpoint ---


def test_trace_returns_result(client: TestClient):
    resp = client.post("/trace", json={"vlan": 254, "source": "onti-be"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["vlan"] == 254
    assert "status" in data
    assert "hops" in data


def test_trace_unknown_vlan(client: TestClient):
    resp = client.post("/trace", json={"vlan": 9999})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "broken"


# --- Diff endpoint ---


def test_diff_no_change(client: TestClient):
    report = {
        "timestamp": "2026-04-08T10:00:00Z",
        "results": [
            {
                "link": "link-1",
                "link_type": "physical_cable",
                "status": "pass",
                "checks": [
                    {
                        "check": "type",
                        "port": "eth1",
                        "expected": "sfp+",
                        "observed": "sfp+",
                        "source": "mcp_live",
                        "flag": "pass",
                    }
                ],
            }
        ],
    }
    resp = client.post("/diff", json={"before": report, "after": report})
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["unchanged"] == 1
    assert data["summary"]["changed"] == 0


def test_diff_with_changes(client: TestClient):
    before = {
        "timestamp": "2026-04-08T10:00:00Z",
        "results": [
            {
                "link": "link-1",
                "link_type": "physical_cable",
                "status": "pass",
                "checks": [
                    {
                        "check": "type",
                        "port": "eth1",
                        "expected": "sfp+",
                        "observed": "sfp+",
                        "source": "mcp_live",
                        "flag": "pass",
                    }
                ],
            }
        ],
    }
    after = {
        "timestamp": "2026-04-08T11:00:00Z",
        "results": [
            {
                "link": "link-1",
                "link_type": "physical_cable",
                "status": "fail",
                "checks": [
                    {
                        "check": "type",
                        "port": "eth1",
                        "expected": "sfp+",
                        "observed": "ethernet",
                        "source": "mcp_live",
                        "flag": "mismatch",
                    }
                ],
            }
        ],
    }
    resp = client.post("/diff", json={"before": before, "after": after})
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["changed"] == 1
    assert data["links"][0]["check_diffs"][0]["before_flag"] == "pass"
    assert data["links"][0]["check_diffs"][0]["after_flag"] == "mismatch"
