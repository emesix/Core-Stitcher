"""Normalize Proxmox node network data into Observation objects.

Converts structured output from proxmox MCP tools (list-bridges, node-status)
into flat Observation records. Handles physical NICs, Linux bridges with
member ports, and VLAN subinterfaces. All vendor-specific mapping stays here.
"""

from __future__ import annotations

from typing import Any

from vos.modelkit.enums import ObservationSource, PortType
from vos.modelkit.observation import Observation


def normalize_network(
    device_slug: str,
    network: list[dict[str, Any]],
) -> list[Observation]:
    """Convert a Proxmox network interface list to Observations.

    Expected shape: [{"iface", "type", "method", "address", "bridge_ports", ...}]
    """
    observations: list[Observation] = []

    for iface in network:
        name = iface.get("iface", "")
        iface_type = iface.get("type", "")

        if not name or iface_type == "loopback":
            continue

        active = iface.get("active", 0)
        port_type = _classify_port(iface_type, name)

        observations.append(_obs(device_slug, "type", port_type.value, port=name))
        observations.append(_obs(device_slug, "device_name", name, port=name))
        observations.append(
            _obs(
                device_slug,
                "status",
                "up" if active else "down",
                port=name,
            )
        )

        # IP address
        address = iface.get("address")
        if address:
            netmask = iface.get("netmask", "")
            prefix = _netmask_to_prefix(netmask) if netmask else ""
            addr_str = f"{address}/{prefix}" if prefix else address
            observations.append(_obs(device_slug, "addr4", addr_str, port=name))

        # Bridge members
        bridge_ports = iface.get("bridge_ports", "")
        if bridge_ports and iface_type == "bridge":
            members = bridge_ports.split()
            observations.append(_obs(device_slug, "bridge_members", sorted(members), port=name))

        # VLAN interface: extract tag from name (e.g. enp2s0.25 → VLAN 25)
        if iface_type == "vlan" and "." in name:
            parent, tag_str = name.rsplit(".", 1)
            try:
                tag = int(tag_str)
                observations.append(
                    _obs(
                        device_slug,
                        "vlans",
                        {"mode": "access", "access_vlan": tag},
                        port=name,
                    )
                )
                observations.append(_obs(device_slug, "vlan_parent", parent, port=name))
            except ValueError:
                pass

    return observations


def normalize_node_identity(
    device_slug: str,
    node_status: dict[str, Any],
    *,
    device_name: str | None = None,
    management_ip: str | None = None,
) -> list[Observation]:
    """Produce device-level identity observations from node-status."""
    observations: list[Observation] = [
        _obs(device_slug, "type", "proxmox", port=None),
    ]

    if device_name:
        observations.append(_obs(device_slug, "name", device_name, port=None))
    if management_ip:
        observations.append(_obs(device_slug, "management_ip", management_ip, port=None))

    pve_version = node_status.get("pveversion")
    if pve_version:
        observations.append(_obs(device_slug, "model", pve_version, port=None))

    uptime = node_status.get("uptime")
    if uptime is not None:
        observations.append(_obs(device_slug, "reachable", True, port=None))

    return observations


def _classify_port(iface_type: str, name: str) -> PortType:
    if iface_type == "bridge" or name.startswith("vmbr"):
        return PortType.BRIDGE
    if iface_type == "vlan" or "." in name:
        return PortType.VLAN
    if name.startswith(("tap", "veth")):
        return PortType.VIRTUAL
    return PortType.SFP_PLUS


_NETMASK_MAP = {
    "255.255.255.0": "24",
    "255.255.0.0": "16",
    "255.0.0.0": "8",
    "255.255.255.128": "25",
    "255.255.255.192": "26",
    "255.255.255.224": "27",
    "255.255.255.240": "28",
    "255.255.255.248": "29",
    "255.255.255.252": "30",
}


def _netmask_to_prefix(netmask: str) -> str:
    return _NETMASK_MAP.get(netmask, "24")


def _obs(
    device: str,
    field: str,
    value: Any,
    *,
    port: str | None = None,
) -> Observation:
    return Observation(
        device=device,
        port=port,
        field=field,
        value=value,
        source=ObservationSource.MCP_LIVE,
        adapter="proxmoxcraft",
    )
