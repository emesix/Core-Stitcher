"""Three-adapter workflow test: switchcraft + opnsensecraft + proxmoxcraft.

Proves that observations from all three adapter types merge correctly
and verifykit can verify links across all device types: switch↔firewall,
switch↔hypervisor, and bridge membership within the hypervisor.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from stitch.apps.preflight import PreflightWorkflow
from stitch.opnsensecraft.normalizer import normalize_device_identity as opnsense_identity
from stitch.opnsensecraft.normalizer import normalize_interfaces
from stitch.proxmoxcraft.normalizer import normalize_network
from stitch.proxmoxcraft.normalizer import normalize_node_identity as proxmox_identity
from stitch.switchcraft.normalizer import normalize_ports, normalize_status, normalize_vlans

if TYPE_CHECKING:
    from stitch.modelkit.observation import Observation

TOPO_FIXTURE = Path(__file__).parent.parent / "fixtures" / "topology_sample.json"
SWITCH_FIXTURE = Path(__file__).parent.parent / "fixtures" / "switchcraft_onti_backend.json"
OPNSENSE_FIXTURE = Path(__file__).parent.parent / "fixtures" / "opnsense_interfaces.json"
PROXMOX_FIXTURE = Path(__file__).parent.parent / "fixtures" / "proxmox_pve_hx310_db.json"


class FixtureCollector:
    def __init__(self, observations: list[Observation]) -> None:
        self._observations = observations

    async def collect(self) -> list[Observation]:
        return self._observations


def _switch_observations() -> list[Observation]:
    fixture = json.loads(SWITCH_FIXTURE.read_text())
    obs: list[Observation] = []
    obs.extend(normalize_status("onti-be", fixture["device_status"], device_name="ONTI-BE"))
    obs.extend(normalize_ports("onti-be", fixture["get_ports"]))
    obs.extend(normalize_vlans("onti-be", fixture["get_vlans"]))
    return obs


def _opnsense_observations() -> list[Observation]:
    fixture = json.loads(OPNSENSE_FIXTURE.read_text())
    obs: list[Observation] = []
    obs.extend(opnsense_identity("opnsense", device_name="OPNsense"))
    obs.extend(normalize_interfaces("opnsense", fixture))
    return obs


def _proxmox_observations() -> list[Observation]:
    fixture = json.loads(PROXMOX_FIXTURE.read_text())
    obs: list[Observation] = []
    obs.extend(
        proxmox_identity(
            "pve-hx310-db",
            fixture["node_status"],
            device_name="PVE-HX310-DB",
        )
    )
    obs.extend(normalize_network("pve-hx310-db", fixture["network"]))
    return obs


async def test_three_adapters_merge():
    """All three adapter types merge into one observed snapshot."""
    workflow = PreflightWorkflow(
        TOPO_FIXTURE,
        collectors=[
            FixtureCollector(_switch_observations()),
            FixtureCollector(_opnsense_observations()),
            FixtureCollector(_proxmox_observations()),
        ],
    )

    report = await workflow.run_verification()

    # All 3 links in the topology should be verified
    assert report.summary["total"] == 3
    assert len(report.results) == 3


async def test_switch_to_firewall_link():
    """Physical cable between onti-be/eth1 and opnsense/ix1 verified."""
    workflow = PreflightWorkflow(
        TOPO_FIXTURE,
        collectors=[
            FixtureCollector(_switch_observations()),
            FixtureCollector(_opnsense_observations()),
            FixtureCollector(_proxmox_observations()),
        ],
    )

    report = await workflow.run_verification()

    link = next(r for r in report.results if r.link == "phys-opnsense-ix1-to-onti-be-eth1")
    port_checks = [c for c in link.checks if c.check == "port_exists"]
    assert all(c.flag == "ok" for c in port_checks)


async def test_switch_to_proxmox_link():
    """Physical cable between onti-be/eth2 and pve-hx310-db/enp2s0 verified."""
    workflow = PreflightWorkflow(
        TOPO_FIXTURE,
        collectors=[
            FixtureCollector(_switch_observations()),
            FixtureCollector(_opnsense_observations()),
            FixtureCollector(_proxmox_observations()),
        ],
    )

    report = await workflow.run_verification()

    link = next(r for r in report.results if r.link == "phys-onti-be-eth2-to-pve-hx310-db-enp2s0")
    port_checks = [c for c in link.checks if c.check == "port_exists"]
    assert all(c.flag == "ok" for c in port_checks)


async def test_bridge_membership_link():
    """Bridge link between pve-hx310-db/enp2s0 and pve-hx310-db/vmbr0 verified."""
    workflow = PreflightWorkflow(
        TOPO_FIXTURE,
        collectors=[
            FixtureCollector(_switch_observations()),
            FixtureCollector(_opnsense_observations()),
            FixtureCollector(_proxmox_observations()),
        ],
    )

    report = await workflow.run_verification()

    link = next(r for r in report.results if r.link == "bridge-pve-hx310-db-enp2s0-to-vmbr0")
    assert link.link_type == "bridge_member"
    assert len(link.checks) > 0


async def test_observed_snapshot_has_all_three():
    """Merged observed snapshot contains devices from all three adapters."""
    from stitch.collectkit.merger import merge_observations

    all_obs = _switch_observations() + _opnsense_observations() + _proxmox_observations()
    snapshot, _conflicts = merge_observations(all_obs)

    assert "onti-be" in snapshot.devices
    assert "opnsense" in snapshot.devices
    assert "pve-hx310-db" in snapshot.devices

    assert snapshot.devices["onti-be"].type == "switch"
    assert snapshot.devices["opnsense"].type == "firewall"
    assert snapshot.devices["pve-hx310-db"].type == "proxmox"


async def test_adapter_attribution():
    """Each adapter's observations carry the correct adapter tag."""
    switch_obs = _switch_observations()
    opnsense_obs = _opnsense_observations()
    proxmox_obs = _proxmox_observations()

    assert all(o.adapter == "switchcraft" for o in switch_obs)
    assert all(o.adapter == "opnsensecraft" for o in opnsense_obs)
    assert all(o.adapter == "proxmoxcraft" for o in proxmox_obs)
