"""Topology diagnostics — dangling ports, orphan devices, missing endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from vos.modelkit.explorer import DanglingPort, TopologyDiagnostics

if TYPE_CHECKING:
    from vos.modelkit.topology import TopologySnapshot


def dangling_ports(snapshot: TopologySnapshot) -> list[DanglingPort]:
    """Find ports that have no links attached."""
    linked: set[tuple[str, str]] = set()
    for link in snapshot.links:
        for ep in link.endpoints:
            linked.add((ep.device, ep.port))

    result: list[DanglingPort] = []
    for dev_name, device in sorted(snapshot.devices.items()):
        for port_name in sorted(device.ports):
            if (dev_name, port_name) not in linked:
                result.append(
                    DanglingPort(device=dev_name, port=port_name, reason="No links attached")
                )
    return result


def orphan_devices(snapshot: TopologySnapshot) -> list[str]:
    """Find devices that appear in no link endpoints."""
    linked_devices: set[str] = set()
    for link in snapshot.links:
        for ep in link.endpoints:
            linked_devices.add(ep.device)

    return sorted(dev for dev in snapshot.devices if dev not in linked_devices)


def missing_endpoints(snapshot: TopologySnapshot) -> list[str]:
    """Find link endpoints that reference non-existent devices or ports."""
    result: list[str] = []
    for link in snapshot.links:
        for ep in link.endpoints:
            device = snapshot.devices.get(ep.device)
            if device is None:
                result.append(f"{link.id}: device '{ep.device}' not found")
            elif ep.port not in device.ports:
                result.append(f"{link.id}: port '{ep.device}/{ep.port}' not found")
    return result


def diagnostics(snapshot: TopologySnapshot) -> TopologyDiagnostics:
    """Full topology health diagnostics."""
    total_ports = sum(len(d.ports) for d in snapshot.devices.values())
    return TopologyDiagnostics(
        dangling_ports=dangling_ports(snapshot),
        orphan_devices=orphan_devices(snapshot),
        missing_endpoints=missing_endpoints(snapshot),
        total_devices=len(snapshot.devices),
        total_ports=total_ports,
        total_links=len(snapshot.links),
    )
