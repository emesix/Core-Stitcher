from __future__ import annotations

from datetime import UTC, datetime

from stitch.modelkit.device import Device
from stitch.modelkit.enums import DeviceType, LinkType
from stitch.modelkit.link import Link, LinkEndpoint
from stitch.modelkit.topology import TopologyMeta, TopologySnapshot
from stitch.modelkit.vlan import VlanMetadata


def test_topology_meta_minimal():
    meta = TopologyMeta(version="1.0", name="lab")
    assert meta.version == "1.0"
    assert meta.name == "lab"
    assert meta.updated is None
    assert meta.updated_by is None


def test_topology_meta_full():
    now = datetime.now(UTC)
    meta = TopologyMeta(version="2.0", name="homelab", updated=now, updated_by="emesix")
    assert meta.updated == now
    assert meta.updated_by == "emesix"


def test_topology_meta_frozen():
    meta = TopologyMeta(version="1.0", name="lab")
    import pytest

    with pytest.raises(Exception):
        meta.version = "2.0"  # type: ignore[misc]


def test_topology_snapshot_minimal():
    meta = TopologyMeta(version="1.0", name="test")
    snap = TopologySnapshot(meta=meta, devices={}, links=[], vlans={})
    assert snap.meta == meta
    assert snap.devices == {}
    assert snap.links == []
    assert snap.vlans == {}


def test_topology_snapshot_full():
    meta = TopologyMeta(version="1.0", name="test")
    device = Device(id="switch-a", name="Switch A", type=DeviceType.SWITCH)
    ep1 = LinkEndpoint(device="switch-a", port="eth0")
    ep2 = LinkEndpoint(device="switch-b", port="eth0")
    link = Link(id="l1", type=LinkType.PHYSICAL_CABLE, endpoints=(ep1, ep2))
    vlan = VlanMetadata(name="management")
    snap = TopologySnapshot(
        meta=meta,
        devices={"switch-a": device},
        links=[link],
        vlans={"10": vlan},
    )
    assert "switch-a" in snap.devices
    assert len(snap.links) == 1
    assert "10" in snap.vlans
