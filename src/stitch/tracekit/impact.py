"""Impact preview engine — deterministic "what breaks if" analysis.

Given a TopologySnapshot and an ImpactRequest, computes which links,
devices, and VLANs are affected by the proposed change. Pure function,
explicit input only, no I/O.

Supported actions:
- remove_link: what breaks if link X is removed
- remove_vlan: what breaks if VLAN N is removed from device/port
- remove_port: what breaks if port P is removed from device
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from stitch.modelkit.impact import ImpactEffect, ImpactRequest, ImpactResult

if TYPE_CHECKING:
    from stitch.modelkit.link import Link
    from stitch.modelkit.topology import TopologySnapshot


_SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def preview_impact(snapshot: TopologySnapshot, request: ImpactRequest) -> ImpactResult:
    if request.action == "remove_link":
        result = _preview_remove_link(snapshot, request)
    elif request.action == "remove_vlan":
        result = _preview_remove_vlan(snapshot, request)
    elif request.action == "remove_port":
        result = _preview_remove_port(snapshot, request)
    else:
        result = ImpactResult(
            proposed_change=request,
            impact=[],
            risk="low",
            safe_to_apply=True,
        )

    return _finalize(result)


def _preview_remove_link(
    snapshot: TopologySnapshot,
    request: ImpactRequest,
) -> ImpactResult:
    link_id = request.parameters.get("link_id", "")
    link = _find_link(snapshot, link_id)

    if link is None:
        return ImpactResult(
            proposed_change=request,
            impact=[],
            risk="low",
            safe_to_apply=True,
        )

    effects: list[ImpactEffect] = []
    ep_a, ep_b = link.endpoints

    # Both endpoints lose this connection
    effects.append(
        ImpactEffect(
            device=ep_a.device,
            port=ep_a.port,
            effect=f"Loses link '{link_id}' to {ep_b.device}/{ep_b.port}",
            severity="error",
        )
    )
    effects.append(
        ImpactEffect(
            device=ep_b.device,
            port=ep_b.port,
            effect=f"Loses link '{link_id}' to {ep_a.device}/{ep_a.port}",
            severity="error",
        )
    )

    # Check what VLANs traverse this link
    vlans_on_link = _vlans_on_link(snapshot, link)
    for vlan_id in sorted(vlans_on_link):
        # Check if there's an alternate path for this VLAN between the two endpoints
        has_alt = _has_alternate_vlan_path(
            snapshot,
            ep_a.device,
            ep_b.device,
            vlan_id,
            exclude_link=link_id,
        )
        if not has_alt:
            effects.append(
                ImpactEffect(
                    device=ep_b.device,
                    port=ep_b.port,
                    effect=f"VLAN {vlan_id} loses reachability from {ep_a.device}",
                    severity="error",
                )
            )

    risk = "high" if len(vlans_on_link) > 0 else "medium"
    return ImpactResult(
        proposed_change=request,
        impact=effects,
        risk=risk,
        safe_to_apply=False,
    )


def _preview_remove_vlan(
    snapshot: TopologySnapshot,
    request: ImpactRequest,
) -> ImpactResult:
    device_name = request.device
    port_name = request.port
    vlan_id = request.parameters.get("vlan_id")

    if port_name is None or vlan_id is None:
        return ImpactResult(
            proposed_change=request,
            impact=[],
            risk="low",
            safe_to_apply=True,
        )

    # Check if this port actually carries the VLAN
    device = snapshot.devices.get(device_name)
    if device is None:
        return ImpactResult(
            proposed_change=request,
            impact=[],
            risk="low",
            safe_to_apply=True,
        )

    port = device.ports.get(port_name)
    if port is None or port.vlans is None:
        return ImpactResult(
            proposed_change=request,
            impact=[],
            risk="low",
            safe_to_apply=True,
        )

    carries = (port.vlans.mode == "trunk" and vlan_id in port.vlans.tagged) or (
        port.vlans.mode == "access" and port.vlans.access_vlan == vlan_id
    )

    if not carries:
        return ImpactResult(
            proposed_change=request,
            impact=[],
            risk="low",
            safe_to_apply=True,
        )

    effects: list[ImpactEffect] = []

    # This port loses the VLAN
    effects.append(
        ImpactEffect(
            device=device_name,
            port=port_name,
            effect=f"VLAN {vlan_id} removed from port",
            severity="warning",
        )
    )

    # Find connected devices that rely on this VLAN through this port
    for link in snapshot.links:
        ep_a, ep_b = link.endpoints
        remote = None
        if ep_a.device == device_name and ep_a.port == port_name:
            remote = ep_b
        elif ep_b.device == device_name and ep_b.port == port_name:
            remote = ep_a
        else:
            continue

        remote_dev = snapshot.devices.get(remote.device)
        if remote_dev is None:
            continue
        remote_port = remote_dev.ports.get(remote.port)
        if remote_port is None or remote_port.vlans is None:
            continue

        remote_carries = (
            remote_port.vlans.mode == "trunk" and vlan_id in remote_port.vlans.tagged
        ) or (remote_port.vlans.mode == "access" and remote_port.vlans.access_vlan == vlan_id)

        if remote_carries:
            effects.append(
                ImpactEffect(
                    device=remote.device,
                    port=remote.port,
                    effect=f"VLAN {vlan_id} loses path from {device_name}/{port_name}",
                    severity="error",
                )
            )

    risk = "high" if len(effects) > 1 else "medium"
    return ImpactResult(
        proposed_change=request,
        impact=effects,
        risk=risk,
        safe_to_apply=len(effects) <= 1,
    )


def _preview_remove_port(
    snapshot: TopologySnapshot,
    request: ImpactRequest,
) -> ImpactResult:
    device_name = request.device
    port_name = request.port

    if port_name is None:
        return ImpactResult(
            proposed_change=request,
            impact=[],
            risk="low",
            safe_to_apply=True,
        )

    device = snapshot.devices.get(device_name)
    if device is None or port_name not in device.ports:
        return ImpactResult(
            proposed_change=request,
            impact=[],
            risk="low",
            safe_to_apply=True,
        )

    effects: list[ImpactEffect] = []

    # Find all links connected to this port
    connected_links = [
        link
        for link in snapshot.links
        if any(ep.device == device_name and ep.port == port_name for ep in link.endpoints)
    ]

    # The port itself goes down
    effects.append(
        ImpactEffect(
            device=device_name,
            port=port_name,
            effect=f"Port '{port_name}' removed from {device_name}",
            severity="error",
        )
    )

    # Each connected link breaks
    for link in connected_links:
        ep_a, ep_b = link.endpoints
        remote = ep_b if (ep_a.device == device_name and ep_a.port == port_name) else ep_a
        effects.append(
            ImpactEffect(
                device=remote.device,
                port=remote.port,
                effect=f"Loses link '{link.id}' to {device_name}/{port_name}",
                severity="error",
            )
        )

    # VLAN reachability impact
    port_vlans = _port_vlans(snapshot, device_name, port_name)
    for vlan_id in sorted(port_vlans):
        for link in connected_links:
            ep_a, ep_b = link.endpoints
            remote = ep_b if (ep_a.device == device_name and ep_a.port == port_name) else ep_a
            has_alt = _has_alternate_vlan_path(
                snapshot,
                device_name,
                remote.device,
                vlan_id,
                exclude_link=link.id,
            )
            if not has_alt:
                effects.append(
                    ImpactEffect(
                        device=remote.device,
                        port=remote.port,
                        effect=f"VLAN {vlan_id} loses reachability from {device_name}",
                        severity="error",
                    )
                )

    if not connected_links:
        return ImpactResult(
            proposed_change=request,
            impact=effects,
            risk="low",
            safe_to_apply=True,
        )

    risk = "high" if port_vlans else "medium"
    return ImpactResult(
        proposed_change=request,
        impact=effects,
        risk=risk,
        safe_to_apply=False,
    )


def _find_link(snapshot: TopologySnapshot, link_id: str) -> Link | None:
    for link in snapshot.links:
        if link.id == link_id:
            return link
    return None


def _vlans_on_link(snapshot: TopologySnapshot, link: Link) -> set[int]:
    """Find VLANs carried by both endpoints of a link."""
    ep_a, ep_b = link.endpoints
    vlans_a = _port_vlans(snapshot, ep_a.device, ep_a.port)
    vlans_b = _port_vlans(snapshot, ep_b.device, ep_b.port)
    return vlans_a & vlans_b


def _port_vlans(snapshot: TopologySnapshot, device: str, port: str) -> set[int]:
    dev = snapshot.devices.get(device)
    if dev is None:
        return set()
    p = dev.ports.get(port)
    if p is None or p.vlans is None:
        return set()
    if p.vlans.mode == "trunk":
        return set(p.vlans.tagged)
    if p.vlans.mode == "access" and p.vlans.access_vlan is not None:
        return {p.vlans.access_vlan}
    return set()


def _has_alternate_vlan_path(
    snapshot: TopologySnapshot,
    device_a: str,
    device_b: str,
    vlan_id: int,
    *,
    exclude_link: str,
) -> bool:
    """Check if device_b can reach device_a for a VLAN without the excluded link."""
    visited: set[str] = set()
    queue = [device_a]
    visited.add(device_a)

    while queue:
        current = queue.pop(0)
        if current == device_b:
            return True

        for link in snapshot.links:
            if link.id == exclude_link:
                continue
            ep_a, ep_b = link.endpoints
            neighbor_dev = None
            neighbor_port = None
            local_port = None

            if ep_a.device == current:
                neighbor_dev = ep_b.device
                neighbor_port = ep_b.port
                local_port = ep_a.port
            elif ep_b.device == current:
                neighbor_dev = ep_a.device
                neighbor_port = ep_a.port
                local_port = ep_b.port
            else:
                continue

            if neighbor_dev in visited:
                continue

            # Both local and remote ports must carry the VLAN
            if vlan_id in _port_vlans(snapshot, current, local_port) and vlan_id in _port_vlans(
                snapshot, neighbor_dev, neighbor_port
            ):
                visited.add(neighbor_dev)
                queue.append(neighbor_dev)

    return False


def _finalize(result: ImpactResult) -> ImpactResult:
    """Sort effects by severity and add highlights/highest_severity."""
    effects = sorted(result.impact, key=lambda e: _SEVERITY_ORDER.get(e.severity, 9))

    if not effects:
        highest = "info"
        highlights = ["No impact detected"]
    else:
        highest = effects[0].severity  # sorted, so first is most severe
        highlights = _build_impact_highlights(effects)

    return ImpactResult(
        proposed_change=result.proposed_change,
        impact=effects,
        risk=result.risk,
        safe_to_apply=result.safe_to_apply,
        highest_severity=highest,
        highlights=highlights,
    )


def _build_impact_highlights(effects: list[ImpactEffect]) -> list[str]:
    highlights: list[str] = []

    affected_devices = {e.device for e in effects}
    error_count = sum(1 for e in effects if e.severity == "error")
    warning_count = sum(1 for e in effects if e.severity == "warning")

    highlights.append(f"{len(affected_devices)} device(s) affected")

    if error_count:
        highlights.append(f"{error_count} critical effect(s)")
    if warning_count:
        highlights.append(f"{warning_count} warning(s)")

    # Add VLAN-specific highlights
    vlan_effects = [e for e in effects if "VLAN" in e.effect or "vlan" in e.effect]
    if vlan_effects:
        highlights.append(f"{len(vlan_effects)} VLAN-related effect(s)")

    return highlights
