from __future__ import annotations

import pytest

from vos.modelkit.impact import ImpactEffect, ImpactRequest, ImpactResult


def test_impact_request_minimal():
    req = ImpactRequest(action="set_vlan", device="switch-a", parameters={})
    assert req.action == "set_vlan"
    assert req.device == "switch-a"
    assert req.port is None
    assert req.parameters == {}


def test_impact_request_full():
    req = ImpactRequest(
        action="configure_port",
        device="switch-a",
        port="eth0",
        parameters={"vlan": 10, "mode": "access"},
    )
    assert req.port == "eth0"
    assert req.parameters["vlan"] == 10


def test_impact_request_frozen():
    req = ImpactRequest(action="test", device="switch-a", parameters={})
    with pytest.raises(Exception):
        req.action = "other"  # type: ignore[misc]


def test_impact_effect_minimal():
    effect = ImpactEffect(device="switch-b", effect="vlan_traffic_disrupted", severity="high")
    assert effect.device == "switch-b"
    assert effect.effect == "vlan_traffic_disrupted"
    assert effect.severity == "high"
    assert effect.port is None


def test_impact_effect_full():
    effect = ImpactEffect(
        device="switch-b",
        port="eth1",
        effect="link_down",
        severity="critical",
    )
    assert effect.port == "eth1"
    assert effect.severity == "critical"


def test_impact_result_minimal():
    req = ImpactRequest(action="set_vlan", device="switch-a", parameters={})
    result = ImpactResult(proposed_change=req, impact=[], risk="low", safe_to_apply=True)
    assert result.risk == "low"
    assert result.safe_to_apply is True
    assert result.impact == []


def test_impact_result_full():
    req = ImpactRequest(action="configure_port", device="switch-a", port="eth0", parameters={})
    effect1 = ImpactEffect(device="switch-b", effect="vlan_loss", severity="high")
    effect2 = ImpactEffect(
        device="switch-c", port="eth2", effect="connectivity_break", severity="critical"
    )
    result = ImpactResult(
        proposed_change=req,
        impact=[effect1, effect2],
        risk="high",
        safe_to_apply=False,
    )
    assert len(result.impact) == 2
    assert result.safe_to_apply is False
    assert result.risk == "high"
