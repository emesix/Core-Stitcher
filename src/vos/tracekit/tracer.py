"""VLAN path tracer — deterministic topology traversal.

Given a TopologySnapshot and a VLAN ID, traces which ports carry the VLAN
and follows links to find the complete path. Reports hops and break points
where the VLAN is not carried. Pure function, no I/O, explicit input only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vos.modelkit.enums import ObservationSource
from vos.modelkit.trace import BreakPoint, TraceHop, TraceRequest, TraceResult

if TYPE_CHECKING:
    from vos.modelkit.topology import TopologySnapshot


def trace_vlan_path(snapshot: TopologySnapshot, request: TraceRequest) -> TraceResult:
    """Trace a VLAN's path across the declared topology.

    If source is given, starts from that device and follows links.
    If source is None, finds all ports carrying the VLAN.
    """
    vlan_id = request.vlan
    source = request.source

    if source is not None:
        return _trace_from_source(snapshot, vlan_id, source)
    return _trace_all(snapshot, vlan_id)


def _trace_from_source(
    snapshot: TopologySnapshot,
    vlan_id: int,
    source_device: str,
) -> TraceResult:
    device = snapshot.devices.get(source_device)
    if device is None:
        return TraceResult(
            vlan=vlan_id,
            source=source_device,
            status="broken",
            first_break=BreakPoint(
                device=source_device,
                port="*",
                reason=f"Device '{source_device}' not found in topology",
            ),
        )

    # Find ports on source device that carry this VLAN
    source_ports = _ports_carrying_vlan(snapshot, source_device, vlan_id)
    if not source_ports:
        return TraceResult(
            vlan=vlan_id,
            source=source_device,
            status="broken",
            first_break=BreakPoint(
                device=source_device,
                port="*",
                reason=f"VLAN {vlan_id} not found on any port of '{source_device}'",
            ),
        )

    # BFS from source ports across links
    hops: list[TraceHop] = []
    visited: set[tuple[str, str]] = set()
    first_break: BreakPoint | None = None

    # Add source port hops
    for port_name in source_ports:
        key = (source_device, port_name)
        if key not in visited:
            visited.add(key)
            hops.append(
                TraceHop(
                    device=source_device,
                    port=port_name,
                    status="ok",
                    source=ObservationSource.DECLARED,
                )
            )

    # Follow links from visited ports
    queue = list(visited)
    while queue:
        dev, port = queue.pop(0)
        for link in snapshot.links:
            ep_a, ep_b = link.endpoints
            remote = None
            if ep_a.device == dev and ep_a.port == port:
                remote = ep_b
            elif ep_b.device == dev and ep_b.port == port:
                remote = ep_a
            else:
                continue

            remote_key = (remote.device, remote.port)
            if remote_key in visited:
                continue
            visited.add(remote_key)

            if _port_carries_vlan(snapshot, remote.device, remote.port, vlan_id):
                hops.append(
                    TraceHop(
                        device=remote.device,
                        port=remote.port,
                        link=link.id,
                        status="ok",
                        source=ObservationSource.DECLARED,
                    )
                )
                queue.append(remote_key)
            else:
                hops.append(
                    TraceHop(
                        device=remote.device,
                        port=remote.port,
                        link=link.id,
                        status="break",
                        source=ObservationSource.DECLARED,
                        reason=f"VLAN {vlan_id} not carried on {remote.device}/{remote.port}",
                    )
                )
                if first_break is None:
                    first_break = BreakPoint(
                        device=remote.device,
                        port=remote.port,
                        reason=f"VLAN {vlan_id} not carried",
                    )

    status = "broken" if first_break else "complete"
    return TraceResult(
        vlan=vlan_id,
        source=source_device,
        status=status,
        hops=hops,
        first_break=first_break,
    )


def _trace_all(snapshot: TopologySnapshot, vlan_id: int) -> TraceResult:
    """Find all ports carrying a VLAN across the entire topology."""
    hops: list[TraceHop] = []

    for dev_name, device in sorted(snapshot.devices.items()):
        for port_name in sorted(device.ports):
            if _port_carries_vlan(snapshot, dev_name, port_name, vlan_id):
                hops.append(
                    TraceHop(
                        device=dev_name,
                        port=port_name,
                        status="ok",
                        source=ObservationSource.DECLARED,
                    )
                )

    status = "complete" if hops else "broken"
    return TraceResult(vlan=vlan_id, status=status, hops=hops)


def _port_carries_vlan(
    snapshot: TopologySnapshot,
    device: str,
    port: str,
    vlan_id: int,
) -> bool:
    dev = snapshot.devices.get(device)
    if dev is None:
        return False
    p = dev.ports.get(port)
    if p is None or p.vlans is None:
        return False

    if p.vlans.mode == "trunk":
        return vlan_id in p.vlans.tagged
    if p.vlans.mode == "access":
        return p.vlans.access_vlan == vlan_id

    return False


def _ports_carrying_vlan(
    snapshot: TopologySnapshot,
    device: str,
    vlan_id: int,
) -> list[str]:
    dev = snapshot.devices.get(device)
    if dev is None:
        return []
    return [
        name for name in sorted(dev.ports) if _port_carries_vlan(snapshot, device, name, vlan_id)
    ]
