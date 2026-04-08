"""VLAN port queries — find ports carrying a specific VLAN."""

from __future__ import annotations

from typing import TYPE_CHECKING

from vos.modelkit.explorer import VlanPortEntry

if TYPE_CHECKING:
    from vos.modelkit.topology import TopologySnapshot


def _port_carries_vlan(vlans, vlan_id: int) -> bool:
    trunk_match = vlans.mode == "trunk" and vlan_id in vlans.tagged
    access_match = vlans.mode == "access" and vlans.access_vlan == vlan_id
    return trunk_match or access_match


def vlan_ports(snapshot: TopologySnapshot, vlan_id: int) -> list[VlanPortEntry]:
    """Find all ports carrying a specific VLAN across the topology.

    Returns entries sorted by (device, port).
    """
    result: list[VlanPortEntry] = []
    for dev_name, device in sorted(snapshot.devices.items()):
        for port_name, port in sorted(device.ports.items()):
            if port.vlans is None:
                continue
            if _port_carries_vlan(port.vlans, vlan_id):
                result.append(VlanPortEntry(device=dev_name, port=port_name, mode=port.vlans.mode))
    return result
