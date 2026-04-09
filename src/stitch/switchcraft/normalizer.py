"""Normalize switchcraft MCP responses into Observation objects.

Converts the structured output from switchcraft's get-ports, get-vlans,
and device-status MCP tools into flat Observation records suitable for
collectkit's merge pipeline. All vendor-specific field mapping stays here.
"""

from __future__ import annotations

from typing import Any

from vos.modelkit.enums import ObservationSource, PortType
from vos.modelkit.observation import Observation


def normalize_ports(
    device_slug: str,
    ports_response: dict[str, Any],
    *,
    port_type: PortType = PortType.SFP_PLUS,
) -> list[Observation]:
    """Convert a switchcraft get-ports response to Observations.

    Expected shape: {"device_id": str, "ports": [{"name", "enabled", "speed", "description"}]}
    """
    observations: list[Observation] = []
    ports = ports_response.get("ports", [])

    for port in ports:
        port_name = port.get("name", "")
        alias = _port_alias(port_name)

        observations.append(_obs(device_slug, "type", port_type.value, port=alias))

        if port_name:
            observations.append(_obs(device_slug, "device_name", port_name, port=alias))

        if port.get("enabled") is not None:
            observations.append(_obs(device_slug, "enabled", port["enabled"], port=alias))

        if port.get("speed"):
            observations.append(_obs(device_slug, "speed", port["speed"], port=alias))

        desc = port.get("description", "")
        if desc:
            status = "up" if desc.upper() == "UP" else "down" if desc.upper() == "DOWN" else desc
            observations.append(_obs(device_slug, "status", status, port=alias))

    return observations


def normalize_vlans(
    device_slug: str,
    vlans_response: dict[str, Any],
) -> list[Observation]:
    """Convert a switchcraft get-vlans response to per-port VLAN Observations.

    Expected shape: {"device_id": str, "vlans": [{"id", "name", "tagged_ports", "untagged_ports"}]}
    """
    observations: list[Observation] = []
    vlans = vlans_response.get("vlans", [])

    # Build per-port VLAN membership from the VLAN table
    port_vlans: dict[str, _PortVlanAccum] = {}
    for vlan in vlans:
        vlan_id = vlan.get("id")
        if vlan_id is None:
            continue

        for port_name in vlan.get("tagged_ports", []):
            alias = _port_alias(port_name)
            accum = port_vlans.setdefault(alias, _PortVlanAccum())
            accum.tagged.append(vlan_id)

        for port_name in vlan.get("untagged_ports", []):
            alias = _port_alias(port_name)
            accum = port_vlans.setdefault(alias, _PortVlanAccum())
            accum.untagged.append(vlan_id)

    # Emit VLAN membership observations per port
    for alias, accum in port_vlans.items():
        vlans_data = accum.to_membership_dict()
        observations.append(_obs(device_slug, "vlans", vlans_data, port=alias))

    return observations


def normalize_status(
    device_slug: str,
    status_response: dict[str, Any],
    *,
    device_type: str = "switch",
    device_name: str | None = None,
) -> list[Observation]:
    """Convert a switchcraft device-status response to device-level Observations.

    Expected shape: {"device_id": str, "reachable": bool, "uptime": str|None, ...}
    """
    observations: list[Observation] = [
        _obs(device_slug, "type", device_type, port=None),
    ]

    if device_name:
        observations.append(_obs(device_slug, "name", device_name, port=None))

    if status_response.get("reachable") is not None:
        observations.append(_obs(device_slug, "reachable", status_response["reachable"], port=None))

    if status_response.get("firmware"):
        observations.append(_obs(device_slug, "model", status_response["firmware"], port=None))

    return observations


class _PortVlanAccum:
    """Accumulates VLAN membership for a single port."""

    def __init__(self) -> None:
        self.tagged: list[int] = []
        self.untagged: list[int] = []

    def to_membership_dict(self) -> dict[str, Any]:
        if self.tagged:
            # Port is a trunk: tagged VLANs present
            return {
                "mode": "trunk",
                "native": self.untagged[0] if self.untagged else None,
                "tagged": sorted(self.tagged),
            }
        elif len(self.untagged) == 1:
            # Single untagged VLAN → access port
            return {
                "mode": "access",
                "access_vlan": self.untagged[0],
            }
        else:
            # Multiple untagged VLANs (unusual) → treat as trunk with no tagging
            return {
                "mode": "trunk",
                "native": self.untagged[0] if self.untagged else None,
                "tagged": [],
            }


def _port_alias(port_name: str) -> str:
    """Convert vendor port name to a short alias.

    Examples:
        Ethernet1/0/1 → eth1
        Ethernet1/0/8 → eth8
        Port1 → port1
        1/1/5 → ge5
        ge1 → ge1
    """
    name = port_name.strip()

    # ONTI style: Ethernet1/0/N → ethN
    if name.lower().startswith("ethernet"):
        parts = name.split("/")
        if parts:
            return f"eth{parts[-1]}"

    # Brocade style: 1/1/N → geN
    if "/" in name and not name.lower().startswith("ethernet"):
        parts = name.split("/")
        return f"ge{parts[-1]}"

    # JT-COM style: PortN → portN
    if name.lower().startswith("port"):
        return name.lower()

    return name.lower()


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
        adapter="switchcraft",
    )
