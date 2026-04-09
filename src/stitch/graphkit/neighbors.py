"""Neighbor queries — find adjacent devices via links."""

from __future__ import annotations

from typing import TYPE_CHECKING

from stitch.modelkit.explorer import Neighbor

if TYPE_CHECKING:
    from stitch.modelkit.topology import TopologySnapshot


def neighbors(snapshot: TopologySnapshot, device_id: str) -> list[Neighbor]:
    """Return all neighbors of a device, one entry per link."""
    result: list[Neighbor] = []
    for link in snapshot.links:
        ep_a, ep_b = link.endpoints
        if ep_a.device == device_id:
            result.append(
                Neighbor(
                    device=ep_b.device,
                    local_port=ep_a.port,
                    remote_port=ep_b.port,
                    link_id=link.id,
                    link_type=link.type,
                )
            )
        elif ep_b.device == device_id:
            result.append(
                Neighbor(
                    device=ep_a.device,
                    local_port=ep_b.port,
                    remote_port=ep_a.port,
                    link_id=link.id,
                    link_type=link.type,
                )
            )
    return result
