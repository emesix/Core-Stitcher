from __future__ import annotations

from enum import StrEnum

__all__ = [
    "CheckCategory",
    "CheckSeverity",
    "DeviceType",
    "LinkType",
    "ObservationSource",
    "PortType",
    "VlanMode",
]


class DeviceType(StrEnum):
    SWITCH = "switch"
    PROXMOX = "proxmox"
    FIREWALL = "firewall"
    VM = "vm"
    CONTAINER = "container"
    ACCESSPOINT = "accesspoint"
    OTHER = "other"


class PortType(StrEnum):
    SFP_PLUS = "sfp+"
    ETHERNET = "ethernet"
    BRIDGE = "bridge"
    VLAN = "vlan"
    VIRTUAL = "virtual"


class LinkType(StrEnum):
    PHYSICAL_CABLE = "physical_cable"
    BRIDGE_MEMBER = "bridge_member"
    VLAN_PARENT = "vlan_parent"
    INTERNAL_VIRTUAL = "internal_virtual"


class ObservationSource(StrEnum):
    MCP_LIVE = "mcp_live"
    DECLARED = "declared"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class VlanMode(StrEnum):
    TRUNK = "trunk"
    ACCESS = "access"


class CheckSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class CheckCategory(StrEnum):
    ENDPOINT_MISSING = "endpoint_missing"
    NEIGHBOR_MISMATCH = "neighbor_mismatch"
    VLAN_MISMATCH = "vlan_mismatch"
    BRIDGE_MEMBERSHIP_MISMATCH = "bridge_membership_mismatch"
    VLAN_PARENT_MISMATCH = "vlan_parent_mismatch"
