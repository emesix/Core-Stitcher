"""Tests for tracekit VLAN path tracer — deterministic topology traversal.

Tests the first real tracekit slice: given a TopologySnapshot and a VLAN ID,
trace the path across declared links and report hops and break points.
"""

from __future__ import annotations

from stitch.modelkit.device import Device
from stitch.modelkit.enums import DeviceType, LinkType, PortType, VlanMode
from stitch.modelkit.link import Link, LinkEndpoint
from stitch.modelkit.port import Port, VlanMembership
from stitch.modelkit.topology import TopologyMeta, TopologySnapshot
from stitch.modelkit.trace import TraceRequest
from stitch.tracekit.tracer import trace_vlan_path

META = TopologyMeta(version="1.0", name="test")


def _trunk_port(tagged: list[int]) -> Port:
    return Port(
        type=PortType.SFP_PLUS,
        vlans=VlanMembership(mode=VlanMode.TRUNK, native=1, tagged=tagged),
    )


def _access_port(vlan: int) -> Port:
    return Port(
        type=PortType.ETHERNET,
        vlans=VlanMembership(mode=VlanMode.ACCESS, access_vlan=vlan),
    )


def _snap(devices: dict[str, Device], links: list[Link]) -> TopologySnapshot:
    return TopologySnapshot(meta=META, devices=devices, links=links)


# --- Simple two-device path ---


def test_trace_vlan_across_physical_link():
    """VLAN 25 carried on trunk ports across a physical cable."""
    snap = _snap(
        {
            "sw1": Device(
                id="sw1",
                name="SW1",
                type=DeviceType.SWITCH,
                ports={"e1": _trunk_port([25, 254])},
            ),
            "fw1": Device(
                id="fw1",
                name="FW1",
                type=DeviceType.FIREWALL,
                ports={"ix1": _trunk_port([25, 254])},
            ),
        },
        [
            Link(
                id="phys-1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="fw1", port="ix1"),
                ),
            )
        ],
    )

    result = trace_vlan_path(snap, TraceRequest(vlan=25, source="sw1"))

    assert result.vlan == 25
    assert result.status == "complete"
    assert len(result.hops) >= 2
    assert result.first_break is None


def test_trace_vlan_not_on_remote_port():
    """VLAN 25 on sw1/e1 but not on fw1/ix1 → break at fw1."""
    snap = _snap(
        {
            "sw1": Device(
                id="sw1",
                name="SW1",
                type=DeviceType.SWITCH,
                ports={"e1": _trunk_port([25])},
            ),
            "fw1": Device(
                id="fw1",
                name="FW1",
                type=DeviceType.FIREWALL,
                ports={"ix1": _trunk_port([254])},
            ),
        },
        [
            Link(
                id="phys-1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="fw1", port="ix1"),
                ),
            )
        ],
    )

    result = trace_vlan_path(snap, TraceRequest(vlan=25, source="sw1"))

    assert result.status == "broken"
    assert result.first_break is not None
    assert result.first_break.device == "fw1"


def test_trace_vlan_three_device_chain():
    """VLAN 254 traces across sw → fw → pve."""
    snap = _snap(
        {
            "sw1": Device(
                id="sw1",
                name="SW1",
                type=DeviceType.SWITCH,
                ports={"e1": _trunk_port([254]), "e2": _trunk_port([254])},
            ),
            "fw1": Device(
                id="fw1",
                name="FW1",
                type=DeviceType.FIREWALL,
                ports={"ix1": _trunk_port([254])},
            ),
            "pve": Device(
                id="pve",
                name="PVE",
                type=DeviceType.PROXMOX,
                ports={"enp2s0": _trunk_port([254])},
            ),
        },
        [
            Link(
                id="l1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="fw1", port="ix1"),
                ),
            ),
            Link(
                id="l2",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e2"),
                    LinkEndpoint(device="pve", port="enp2s0"),
                ),
            ),
        ],
    )

    result = trace_vlan_path(snap, TraceRequest(vlan=254, source="sw1"))

    assert result.status == "complete"
    devices_in_hops = {h.device for h in result.hops if h.device}
    assert "sw1" in devices_in_hops
    assert "fw1" in devices_in_hops
    assert "pve" in devices_in_hops


def test_trace_unknown_vlan():
    """VLAN not present on any port → no hops."""
    snap = _snap(
        {
            "sw1": Device(
                id="sw1",
                name="SW1",
                type=DeviceType.SWITCH,
                ports={"e1": _trunk_port([25])},
            ),
        },
        [],
    )

    result = trace_vlan_path(snap, TraceRequest(vlan=999, source="sw1"))

    assert result.status == "broken"
    assert len(result.hops) == 0


def test_trace_from_unknown_device():
    """Source device doesn't exist → broken with no hops."""
    snap = _snap({}, [])

    result = trace_vlan_path(snap, TraceRequest(vlan=25, source="nonexistent"))

    assert result.status == "broken"
    assert result.first_break is not None
    assert result.first_break.device == "nonexistent"


def test_trace_without_source():
    """Trace without source finds all devices carrying the VLAN."""
    snap = _snap(
        {
            "sw1": Device(
                id="sw1",
                name="SW1",
                type=DeviceType.SWITCH,
                ports={"e1": _trunk_port([25])},
            ),
            "fw1": Device(
                id="fw1",
                name="FW1",
                type=DeviceType.FIREWALL,
                ports={"ix1": _trunk_port([25])},
            ),
            "pve": Device(
                id="pve",
                name="PVE",
                type=DeviceType.PROXMOX,
                ports={"e1": _trunk_port([254])},
            ),
        },
        [
            Link(
                id="l1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="fw1", port="ix1"),
                ),
            )
        ],
    )

    result = trace_vlan_path(snap, TraceRequest(vlan=25))

    assert result.status == "complete"
    devices = {h.device for h in result.hops if h.device}
    assert "sw1" in devices
    assert "fw1" in devices
    # pve doesn't carry VLAN 25
    assert "pve" not in devices


def test_hops_have_port_info():
    """Each hop should include device and port details."""
    snap = _snap(
        {
            "sw1": Device(
                id="sw1",
                name="SW1",
                type=DeviceType.SWITCH,
                ports={"e1": _trunk_port([25])},
            ),
            "fw1": Device(
                id="fw1",
                name="FW1",
                type=DeviceType.FIREWALL,
                ports={"ix1": _trunk_port([25])},
            ),
        },
        [
            Link(
                id="l1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="fw1", port="ix1"),
                ),
            )
        ],
    )

    result = trace_vlan_path(snap, TraceRequest(vlan=25, source="sw1"))

    for hop in result.hops:
        assert hop.device is not None
        assert hop.port is not None
