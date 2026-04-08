"""Subgraph extraction — filter topology to a subset of devices."""

from __future__ import annotations

from vos.modelkit.topology import TopologyMeta, TopologySnapshot


def subgraph(snapshot: TopologySnapshot, device_ids: set[str]) -> TopologySnapshot:
    """Extract a subset of the topology containing only the specified devices.

    Links are included only if both endpoints are in the device set.
    All VLANs are preserved (they are metadata, not device-scoped).
    """
    devices = {dev_id: dev for dev_id, dev in snapshot.devices.items() if dev_id in device_ids}
    links = [
        link
        for link in snapshot.links
        if link.endpoints[0].device in device_ids and link.endpoints[1].device in device_ids
    ]

    return TopologySnapshot(
        meta=TopologyMeta(
            version=snapshot.meta.version,
            name=f"{snapshot.meta.name} (subgraph)",
        ),
        devices=devices,
        links=links,
        vlans=dict(snapshot.vlans),
    )
