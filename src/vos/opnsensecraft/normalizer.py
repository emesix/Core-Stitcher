"""Normalize OPNsense interface data into Observation objects.

Converts the structured output from opnsense's get-interfaces MCP tool
into flat Observation records. Handles physical ports, VLAN subinterfaces,
and bridge membership. All vendor-specific field mapping stays here.
"""

from __future__ import annotations

import re
from typing import Any

from vos.modelkit.enums import ObservationSource, PortType
from vos.modelkit.observation import Observation


def normalize_interfaces(
    device_slug: str,
    interfaces_response: dict[str, Any],
) -> list[Observation]:
    """Convert an opnsense get-interfaces response to Observations.

    Expected shape: {"rows": [{"device", "status", "macaddr", "media", ...}]}
    """
    observations: list[Observation] = []
    rows = interfaces_response.get("rows", [])

    for iface in rows:
        device_name = iface.get("device", "")
        if not device_name or device_name in ("lo0", "enc0", "pflog0"):
            continue

        enabled = iface.get("enabled", False)
        if not enabled and not iface.get("identifier"):
            continue

        port_type = _classify_port(iface)
        observations.append(_obs(device_slug, "type", port_type.value, port=device_name))
        observations.append(_obs(device_slug, "device_name", device_name, port=device_name))

        status = iface.get("status", "")
        if status:
            normalized = "up" if status == "up" else "down"
            observations.append(_obs(device_slug, "status", normalized, port=device_name))

        mac = iface.get("macaddr")
        if mac and mac != "00:00:00:00:00:00":
            observations.append(_obs(device_slug, "mac", mac, port=device_name))

        speed = _parse_speed(iface.get("media", ""))
        if speed:
            observations.append(_obs(device_slug, "speed", speed, port=device_name))

        # VLAN tag and parent
        vlan_tag = iface.get("vlan_tag")
        vlan_info = iface.get("vlan")
        if vlan_tag is not None and vlan_info:
            tag = int(vlan_tag)
            parent = vlan_info.get("parent", "")
            observations.append(
                _obs(
                    device_slug,
                    "vlans",
                    {"mode": "access", "access_vlan": tag},
                    port=device_name,
                )
            )
            if parent:
                observations.append(
                    _obs(
                        device_slug,
                        "vlan_parent",
                        parent,
                        port=device_name,
                    )
                )
                # Also record that the parent carries this VLAN as tagged
                _add_tagged_vlan(observations, device_slug, parent, tag)

        # Bridge members
        members = iface.get("members")
        if members and isinstance(members, dict):
            observations.append(
                _obs(
                    device_slug,
                    "bridge_members",
                    sorted(members.keys()),
                    port=device_name,
                )
            )

        # IP address
        addr4 = iface.get("addr4", "")
        if addr4:
            observations.append(_obs(device_slug, "addr4", addr4, port=device_name))

        # Description / role
        desc = iface.get("description", "")
        if desc:
            observations.append(_obs(device_slug, "description", desc, port=device_name))

    return observations


def normalize_device_identity(
    device_slug: str,
    *,
    device_name: str | None = None,
    management_ip: str | None = None,
) -> list[Observation]:
    """Produce device-level identity observations."""
    observations: list[Observation] = [
        _obs(device_slug, "type", "firewall", port=None),
    ]
    if device_name:
        observations.append(_obs(device_slug, "name", device_name, port=None))
    if management_ip:
        observations.append(_obs(device_slug, "management_ip", management_ip, port=None))
    return observations


def _classify_port(iface: dict[str, Any]) -> PortType:
    device = iface.get("device", "")
    if iface.get("vlan_tag") is not None:
        return PortType.VLAN
    if iface.get("members"):
        return PortType.BRIDGE
    if device.startswith("vtnet"):
        return PortType.VIRTUAL
    if iface.get("is_physical", False):
        return PortType.SFP_PLUS
    return PortType.ETHERNET


_SPEED_PATTERNS = [
    (re.compile(r"10Gbase", re.IGNORECASE), "10G"),
    (re.compile(r"2500Base", re.IGNORECASE), "2.5G"),
    (re.compile(r"1000base", re.IGNORECASE), "1G"),
    (re.compile(r"100base", re.IGNORECASE), "100M"),
    (re.compile(r"10base", re.IGNORECASE), "10M"),
]


def _parse_speed(media: str) -> str | None:
    for pattern, speed in _SPEED_PATTERNS:
        if pattern.search(media):
            return speed
    return None


def _add_tagged_vlan(
    observations: list[Observation],
    device_slug: str,
    parent_port: str,
    vlan_id: int,
) -> None:
    """Add or update a trunk VLAN membership observation for a parent port."""
    # Find existing VLAN observation for this parent port
    for obs in observations:
        if obs.device == device_slug and obs.port == parent_port and obs.field == "vlans":
            existing = obs.value
            if isinstance(existing, dict) and existing.get("mode") == "trunk":
                tagged = existing.get("tagged", [])
                if vlan_id not in tagged:
                    tagged.append(vlan_id)
                    tagged.sort()
                return

    # No existing trunk observation — create one
    observations.append(
        _obs(
            device_slug,
            "vlans",
            {"mode": "trunk", "native": None, "tagged": [vlan_id]},
            port=parent_port,
        )
    )


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
        adapter="opnsensecraft",
    )
