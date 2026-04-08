from __future__ import annotations

import pytest

from vos.modelkit.enums import LinkType
from vos.modelkit.link import Link, LinkEndpoint


def test_link_endpoint_minimal():
    ep = LinkEndpoint(device="switch-a", port="eth0")
    assert ep.device == "switch-a"
    assert ep.port == "eth0"


def test_link_endpoint_frozen():
    ep = LinkEndpoint(device="switch-a", port="eth0")
    with pytest.raises(Exception):
        ep.device = "switch-b"  # type: ignore[misc]


def test_link_minimal():
    ep1 = LinkEndpoint(device="switch-a", port="eth0")
    ep2 = LinkEndpoint(device="switch-b", port="eth1")
    link = Link(id="link-001", type=LinkType.PHYSICAL_CABLE, endpoints=(ep1, ep2))
    assert link.id == "link-001"
    assert link.type == LinkType.PHYSICAL_CABLE
    assert link.endpoints[0].device == "switch-a"
    assert link.endpoints[1].device == "switch-b"
    assert link.media is None
    assert link.cable_color is None
    assert link.notes is None


def test_link_full():
    ep1 = LinkEndpoint(device="switch-a", port="sfp1")
    ep2 = LinkEndpoint(device="switch-b", port="sfp2")
    link = Link(
        id="link-002",
        type=LinkType.PHYSICAL_CABLE,
        endpoints=(ep1, ep2),
        media="fiber",
        cable_color="yellow",
        notes="Core uplink",
    )
    assert link.media == "fiber"
    assert link.cable_color == "yellow"
    assert link.notes == "Core uplink"


def test_link_bridge_member():
    ep1 = LinkEndpoint(device="pve-node1", port="eth0")
    ep2 = LinkEndpoint(device="pve-node1", port="vmbr0")
    link = Link(id="link-bridge", type=LinkType.BRIDGE_MEMBER, endpoints=(ep1, ep2))
    assert link.type == LinkType.BRIDGE_MEMBER
