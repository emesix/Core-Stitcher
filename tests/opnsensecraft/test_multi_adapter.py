"""Multi-adapter workflow test: switchcraft + opnsensecraft → merged snapshot → verify.

Proves that observations from two different adapter types merge correctly
into a single observed TopologySnapshot and produce a meaningful
VerificationReport covering links between devices from different adapters.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from vos.apps.preflight import PreflightWorkflow
from vos.opnsensecraft.normalizer import normalize_device_identity, normalize_interfaces
from vos.switchcraft.normalizer import normalize_ports, normalize_status, normalize_vlans

if TYPE_CHECKING:
    from vos.modelkit.observation import Observation

TOPO_FIXTURE = Path(__file__).parent.parent / "fixtures" / "topology_sample.json"
SWITCH_FIXTURE = Path(__file__).parent.parent / "fixtures" / "switchcraft_onti_backend.json"
OPNSENSE_FIXTURE = Path(__file__).parent.parent / "fixtures" / "opnsense_interfaces.json"


class FixtureCollector:
    """Collector that returns pre-built observations from fixture data."""

    def __init__(self, observations: list[Observation]) -> None:
        self._observations = observations

    async def collect(self) -> list[Observation]:
        return self._observations


def _switch_observations() -> list[Observation]:
    """Build observations from switchcraft fixture (onti-be switch)."""
    fixture = json.loads(SWITCH_FIXTURE.read_text())
    obs: list[Observation] = []
    obs.extend(
        normalize_status(
            "onti-be",
            fixture["device_status"],
            device_name="ONTI-BE",
        )
    )
    obs.extend(normalize_ports("onti-be", fixture["get_ports"]))
    obs.extend(normalize_vlans("onti-be", fixture["get_vlans"]))
    return obs


def _opnsense_observations() -> list[Observation]:
    """Build observations from opnsensecraft fixture (opnsense firewall)."""
    fixture = json.loads(OPNSENSE_FIXTURE.read_text())
    obs: list[Observation] = []
    obs.extend(
        normalize_device_identity(
            "opnsense",
            device_name="OPNsense",
            management_ip="192.168.254.1",
        )
    )
    obs.extend(normalize_interfaces("opnsense", fixture))
    return obs


async def test_two_adapters_merge():
    """Observations from switchcraft + opnsensecraft merge into one snapshot."""
    switch_collector = FixtureCollector(_switch_observations())
    opnsense_collector = FixtureCollector(_opnsense_observations())

    workflow = PreflightWorkflow(
        TOPO_FIXTURE,
        collectors=[switch_collector, opnsense_collector],
    )

    report = await workflow.run_verification()

    # All 3 links should be verified
    assert report.summary["total"] == 3

    # The physical link between opnsense/ix1 and onti-be/eth1 should have checks
    phys_link = [r for r in report.results if "opnsense" in r.link]
    assert len(phys_link) == 1
    assert len(phys_link[0].checks) > 0


async def test_cross_adapter_link_verified():
    """The physical cable between opnsense and onti-be is verified across adapters."""
    switch_collector = FixtureCollector(_switch_observations())
    opnsense_collector = FixtureCollector(_opnsense_observations())

    workflow = PreflightWorkflow(
        TOPO_FIXTURE,
        collectors=[switch_collector, opnsense_collector],
    )

    report = await workflow.run_verification()

    # Find the opnsense-to-onti link
    cross_link = next(r for r in report.results if r.link == "phys-opnsense-ix1-to-onti-be-eth1")
    # Both endpoints should exist (not missing)
    port_checks = [c for c in cross_link.checks if c.check == "port_exists"]
    assert all(c.flag == "ok" for c in port_checks)


async def test_observed_snapshot_has_both_devices():
    """The merged observed snapshot should contain devices from both adapters."""
    from vos.collectkit.merger import merge_observations

    all_obs = _switch_observations() + _opnsense_observations()
    snapshot, conflicts = merge_observations(all_obs)

    assert "onti-be" in snapshot.devices
    assert "opnsense" in snapshot.devices

    # onti-be comes from switchcraft
    assert snapshot.devices["onti-be"].type == "switch"
    # opnsense comes from opnsensecraft
    assert snapshot.devices["opnsense"].type == "firewall"


async def test_adapter_attribution():
    """Observations from each adapter should have the correct adapter tag."""
    switch_obs = _switch_observations()
    opnsense_obs = _opnsense_observations()

    assert all(o.adapter == "switchcraft" for o in switch_obs)
    assert all(o.adapter == "opnsensecraft" for o in opnsense_obs)
