"""End-to-end tests for the preflight vertical slice.

Uses a fake in-memory collector that produces observations matching (or diverging
from) the sample topology fixture. Tests the full pipeline:
storekit.load → collector.collect → collectkit.merge → verifykit.verify → report.
"""

from __future__ import annotations

from pathlib import Path

from stitch.apps.preflight import PreflightWorkflow
from stitch.modelkit.enums import ObservationSource
from stitch.modelkit.observation import Observation

FIXTURE = Path(__file__).parent.parent.parent / "fixtures" / "topology_sample.json"


class FakeCollector:
    """In-memory collector that returns canned observations."""

    def __init__(self, observations: list[Observation]) -> None:
        self._observations = observations

    async def collect(self) -> list[Observation]:
        return self._observations


def _device_obs(
    device: str,
    device_type: str,
    *,
    name: str | None = None,
    mgmt_ip: str | None = None,
) -> list[Observation]:
    obs = [
        Observation(
            device=device,
            field="type",
            value=device_type,
            source=ObservationSource.MCP_LIVE,
            adapter="fake",
        ),
    ]
    if name:
        obs.append(
            Observation(
                device=device,
                field="name",
                value=name,
                source=ObservationSource.MCP_LIVE,
                adapter="fake",
            )
        )
    if mgmt_ip:
        obs.append(
            Observation(
                device=device,
                field="management_ip",
                value=mgmt_ip,
                source=ObservationSource.MCP_LIVE,
                adapter="fake",
            )
        )
    return obs


def _port_obs(device: str, port: str, port_type: str, **kwargs: object) -> list[Observation]:
    obs = [
        Observation(
            device=device,
            port=port,
            field="type",
            value=port_type,
            source=ObservationSource.MCP_LIVE,
            adapter="fake",
        ),
    ]
    for field, value in kwargs.items():
        obs.append(
            Observation(
                device=device,
                port=port,
                field=field,
                value=value,
                source=ObservationSource.MCP_LIVE,
                adapter="fake",
            )
        )
    return obs


def _matching_observations() -> list[Observation]:
    """Observations that match the sample topology exactly."""
    obs: list[Observation] = []

    # onti-be (switch)
    obs.extend(_device_obs("onti-be", "switch", name="ONTI-BE", mgmt_ip="192.168.254.10"))
    obs.extend(_port_obs("onti-be", "eth1", "sfp+", device_name="ge1"))
    obs.extend(_port_obs("onti-be", "eth2", "sfp+", device_name="ge2"))

    # opnsense (firewall)
    obs.extend(_device_obs("opnsense", "firewall", name="OPNsense", mgmt_ip="192.168.254.1"))
    obs.extend(_port_obs("opnsense", "ix1", "sfp+", device_name="ix1"))

    # pve-hx310-db (proxmox)
    obs.extend(
        _device_obs(
            "pve-hx310-db",
            "proxmox",
            name="PVE-HX310-DB",
            mgmt_ip="192.168.254.20",
        )
    )
    obs.extend(_port_obs("pve-hx310-db", "enp2s0", "sfp+", device_name="enp2s0"))
    obs.extend(_port_obs("pve-hx310-db", "vmbr0", "bridge", device_name="vmbr0"))

    return obs


async def test_happy_path_all_pass():
    """All devices and ports observed matching declared → all links pass."""
    collector = FakeCollector(_matching_observations())
    workflow = PreflightWorkflow(FIXTURE, collectors=[collector])

    report = await workflow.run_verification()

    assert report.summary["total"] == 3
    assert report.summary["pass"] == 3
    assert report.summary["fail"] == 0


async def test_missing_device_causes_failure():
    """If a device is not observed, links involving it should fail."""
    obs = _matching_observations()
    # Remove all opnsense observations
    obs = [o for o in obs if o.device != "opnsense"]

    collector = FakeCollector(obs)
    workflow = PreflightWorkflow(FIXTURE, collectors=[collector])

    report = await workflow.run_verification()

    # The link between opnsense and onti-be should fail
    assert report.summary["fail"] >= 1
    failed = [r for r in report.results if r.status == "fail"]
    assert any("opnsense" in r.link for r in failed)


async def test_missing_port_causes_failure():
    """If a port is not observed, links involving it should fail."""
    obs = _matching_observations()
    # Remove vmbr0 observations
    obs = [o for o in obs if not (o.device == "pve-hx310-db" and o.port == "vmbr0")]

    collector = FakeCollector(obs)
    workflow = PreflightWorkflow(FIXTURE, collectors=[collector])

    report = await workflow.run_verification()

    # Bridge link should fail
    bridge_results = [r for r in report.results if "bridge" in r.link]
    assert len(bridge_results) == 1
    assert bridge_results[0].status == "fail"


async def test_multiple_collectors():
    """Observations from multiple collectors are merged."""
    switch_obs = _device_obs("onti-be", "switch", name="ONTI-BE")
    switch_obs.extend(_port_obs("onti-be", "eth1", "sfp+"))
    switch_obs.extend(_port_obs("onti-be", "eth2", "sfp+"))

    fw_obs = _device_obs("opnsense", "firewall", name="OPNsense")
    fw_obs.extend(_port_obs("opnsense", "ix1", "sfp+"))

    pve_obs = _device_obs("pve-hx310-db", "proxmox", name="PVE-HX310-DB")
    pve_obs.extend(_port_obs("pve-hx310-db", "enp2s0", "sfp+"))
    pve_obs.extend(_port_obs("pve-hx310-db", "vmbr0", "bridge"))

    collectors = [
        FakeCollector(switch_obs),
        FakeCollector(fw_obs),
        FakeCollector(pve_obs),
    ]
    workflow = PreflightWorkflow(FIXTURE, collectors=collectors)

    report = await workflow.run_verification()
    assert report.summary["total"] == 3


async def test_report_has_link_details():
    """Report contains per-link verification with check details."""
    collector = FakeCollector(_matching_observations())
    workflow = PreflightWorkflow(FIXTURE, collectors=[collector])

    report = await workflow.run_verification()

    for result in report.results:
        assert result.link  # has link ID
        assert result.link_type  # has link type
        assert result.status in ("pass", "fail", "warning")
        assert len(result.checks) > 0  # has actual checks


async def test_empty_collectors():
    """No observations at all → all links fail with missing devices."""
    collector = FakeCollector([])
    workflow = PreflightWorkflow(FIXTURE, collectors=[collector])

    report = await workflow.run_verification()

    assert report.summary["total"] == 3
    assert report.summary["fail"] == 3


async def test_declared_topology_property():
    """Can access the declared topology directly."""
    collector = FakeCollector([])
    workflow = PreflightWorkflow(FIXTURE, collectors=[collector])

    snap = workflow.declared_topology
    assert snap.meta.name == "homelab-sample"
    assert len(snap.devices) == 3


async def test_trace_vlan_through_workflow():
    from stitch.modelkit.trace import TraceRequest

    collector = FakeCollector([])
    workflow = PreflightWorkflow(FIXTURE, collectors=[collector])

    result = await workflow.run_trace(TraceRequest(vlan=254, source="onti-be"))
    assert result.vlan == 254
    assert result.status in ("complete", "broken")
    assert len(result.hops) >= 0


async def test_impact_preview_through_workflow():
    from stitch.modelkit.impact import ImpactRequest

    collector = FakeCollector([])
    workflow = PreflightWorkflow(FIXTURE, collectors=[collector])

    result = await workflow.run_impact_preview(
        ImpactRequest(
            action="remove_link",
            device="onti-be",
            parameters={"link_id": "phys-opnsense-ix1-to-onti-be-eth1"},
        )
    )
    assert result.proposed_change.action == "remove_link"
    assert len(result.impact) > 0
    assert result.risk in ("high", "medium", "low")
