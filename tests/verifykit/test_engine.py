from __future__ import annotations

from vos.modelkit.device import Device
from vos.modelkit.enums import DeviceType, LinkType, PortType, VlanMode
from vos.modelkit.link import Link, LinkEndpoint
from vos.modelkit.port import ExpectedNeighbor, Port, VlanMembership
from vos.modelkit.topology import TopologyMeta, TopologySnapshot
from vos.verifykit.engine import verify_topology

META = TopologyMeta(version="1.0", name="test")


def _trunk_port(tagged: list[int], *, neighbor: ExpectedNeighbor | None = None) -> Port:
    return Port(
        type=PortType.SFP_PLUS,
        vlans=VlanMembership(mode=VlanMode.TRUNK, native=1, tagged=tagged),
        expected_neighbor=neighbor,
    )


def _make_snapshot(
    devices: dict[str, Device],
    links: list[Link] | None = None,
) -> TopologySnapshot:
    return TopologySnapshot(meta=META, devices=devices, links=links or [])


def test_empty_topology():
    declared = _make_snapshot({})
    observed = _make_snapshot({})
    report = verify_topology(declared, observed)
    assert len(report.results) == 0
    assert report.summary["total"] == 0


def test_physical_cable_all_ok():
    devices = {
        "sw1": Device(
            id="sw1",
            name="SW1",
            type=DeviceType.SWITCH,
            ports={
                "eth1": _trunk_port(
                    [25, 254],
                    neighbor=ExpectedNeighbor(device="fw1", port="ix1"),
                ),
            },
        ),
        "fw1": Device(
            id="fw1",
            name="FW1",
            type=DeviceType.FIREWALL,
            ports={
                "ix1": _trunk_port(
                    [25, 254],
                    neighbor=ExpectedNeighbor(device="sw1", port="eth1"),
                ),
            },
        ),
    }
    links = [
        Link(
            id="phys-sw1-eth1-fw1-ix1",
            type=LinkType.PHYSICAL_CABLE,
            endpoints=(
                LinkEndpoint(device="sw1", port="eth1"),
                LinkEndpoint(device="fw1", port="ix1"),
            ),
        ),
    ]
    declared = _make_snapshot(devices, links)
    observed = _make_snapshot(devices)  # same devices observed

    report = verify_topology(declared, observed)
    assert report.summary["total"] == 1
    assert report.summary["pass"] == 1
    link_result = report.results[0]
    assert link_result.status == "pass"


def test_missing_device_in_observed():
    devices_declared = {
        "sw1": Device(
            id="sw1",
            name="SW1",
            type=DeviceType.SWITCH,
            ports={"eth1": _trunk_port([25])},
        ),
        "fw1": Device(
            id="fw1",
            name="FW1",
            type=DeviceType.FIREWALL,
            ports={"ix1": _trunk_port([25])},
        ),
    }
    links = [
        Link(
            id="phys-1",
            type=LinkType.PHYSICAL_CABLE,
            endpoints=(
                LinkEndpoint(device="sw1", port="eth1"),
                LinkEndpoint(device="fw1", port="ix1"),
            ),
        ),
    ]
    declared = _make_snapshot(devices_declared, links)
    # fw1 not in observed
    observed = _make_snapshot(
        {
            "sw1": Device(
                id="sw1",
                name="SW1",
                type=DeviceType.SWITCH,
                ports={"eth1": _trunk_port([25])},
            ),
        }
    )

    report = verify_topology(declared, observed)
    assert report.summary["fail"] == 1
    flags = {c.flag for r in report.results for c in r.checks}
    assert "missing" in flags


def test_missing_port_in_observed():
    devices_declared = {
        "sw1": Device(
            id="sw1",
            name="SW1",
            type=DeviceType.SWITCH,
            ports={"eth1": _trunk_port([25]), "eth2": _trunk_port([25])},
        ),
    }
    links = [
        Link(
            id="bridge-1",
            type=LinkType.BRIDGE_MEMBER,
            endpoints=(
                LinkEndpoint(device="sw1", port="eth1"),
                LinkEndpoint(device="sw1", port="eth2"),
            ),
        ),
    ]
    declared = _make_snapshot(devices_declared, links)
    # eth2 missing in observed
    observed = _make_snapshot(
        {
            "sw1": Device(
                id="sw1",
                name="SW1",
                type=DeviceType.SWITCH,
                ports={"eth1": _trunk_port([25])},
            ),
        }
    )

    report = verify_topology(declared, observed)
    assert report.summary["fail"] == 1


def test_vlan_incompatibility():
    devices = {
        "sw1": Device(
            id="sw1",
            name="SW1",
            type=DeviceType.SWITCH,
            ports={"eth1": _trunk_port([25])},
        ),
        "sw2": Device(
            id="sw2",
            name="SW2",
            type=DeviceType.SWITCH,
            ports={"eth1": _trunk_port([254])},
        ),
    }
    links = [
        Link(
            id="phys-1",
            type=LinkType.PHYSICAL_CABLE,
            endpoints=(
                LinkEndpoint(device="sw1", port="eth1"),
                LinkEndpoint(device="sw2", port="eth1"),
            ),
        ),
    ]
    declared = _make_snapshot(devices, links)
    observed = _make_snapshot(devices)

    report = verify_topology(declared, observed)
    # Should have a warning for no shared VLANs
    link_result = report.results[0]
    vlan_checks = [c for c in link_result.checks if c.check == "vlan_compatibility"]
    assert len(vlan_checks) == 1
    assert vlan_checks[0].flag == "warning"


def test_neighbor_mismatch():
    devices = {
        "sw1": Device(
            id="sw1",
            name="SW1",
            type=DeviceType.SWITCH,
            ports={
                "eth1": _trunk_port(
                    [25],
                    neighbor=ExpectedNeighbor(device="fw1", port="ix1"),
                ),
            },
        ),
        "sw2": Device(
            id="sw2",
            name="SW2",
            type=DeviceType.SWITCH,
            ports={"eth1": _trunk_port([25])},
        ),
    }
    links = [
        Link(
            id="phys-1",
            type=LinkType.PHYSICAL_CABLE,
            endpoints=(
                LinkEndpoint(device="sw1", port="eth1"),
                LinkEndpoint(device="sw2", port="eth1"),
            ),
        ),
    ]
    declared = _make_snapshot(devices, links)
    observed = _make_snapshot(devices)

    report = verify_topology(declared, observed)
    neighbor_checks = [c for r in report.results for c in r.checks if c.check == "neighbor_match"]
    assert any(c.flag == "mismatch" for c in neighbor_checks)


def test_bridge_member_ok():
    devices = {
        "pve": Device(
            id="pve",
            name="PVE",
            type=DeviceType.PROXMOX,
            ports={
                "enp2s0": Port(type=PortType.SFP_PLUS),
                "vmbr0": Port(type=PortType.BRIDGE),
            },
        ),
    }
    links = [
        Link(
            id="bridge-1",
            type=LinkType.BRIDGE_MEMBER,
            endpoints=(
                LinkEndpoint(device="pve", port="enp2s0"),
                LinkEndpoint(device="pve", port="vmbr0"),
            ),
        ),
    ]
    declared = _make_snapshot(devices, links)
    observed = _make_snapshot(devices)

    report = verify_topology(declared, observed)
    assert report.summary["pass"] == 1


def test_summary_counts():
    devices = {
        "sw1": Device(
            id="sw1",
            name="SW1",
            type=DeviceType.SWITCH,
            ports={"eth1": _trunk_port([25, 254])},
        ),
        "fw1": Device(
            id="fw1",
            name="FW1",
            type=DeviceType.FIREWALL,
            ports={"ix1": _trunk_port([25, 254])},
        ),
    }
    links = [
        Link(
            id="link-ok",
            type=LinkType.PHYSICAL_CABLE,
            endpoints=(
                LinkEndpoint(device="sw1", port="eth1"),
                LinkEndpoint(device="fw1", port="ix1"),
            ),
        ),
        Link(
            id="link-missing",
            type=LinkType.PHYSICAL_CABLE,
            endpoints=(
                LinkEndpoint(device="sw1", port="eth1"),
                LinkEndpoint(device="ghost", port="eth0"),
            ),
        ),
    ]
    declared = _make_snapshot(devices, links)
    observed = _make_snapshot(devices)

    report = verify_topology(declared, observed)
    assert report.summary["total"] == 2
    assert report.summary["pass"] == 1
    assert report.summary["fail"] == 1
