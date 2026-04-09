from __future__ import annotations

from vos.modelkit.device import Device, Position
from vos.modelkit.enums import (
    CheckCategory,
    CheckSeverity,
    DeviceType,
    LinkType,
    ObservationSource,
    PortType,
    VlanMode,
)
from vos.modelkit.explorer import DanglingPort, Neighbor, TopologyDiagnostics, VlanPortEntry
from vos.modelkit.impact import ImpactEffect, ImpactRequest, ImpactResult
from vos.modelkit.link import Link, LinkEndpoint
from vos.modelkit.observation import MergeConflict, Mismatch, Observation
from vos.modelkit.port import ExpectedNeighbor, Port, VlanMembership
from vos.modelkit.topology import TopologyMeta, TopologySnapshot
from vos.modelkit.trace import BreakPoint, TraceHop, TraceRequest, TraceResult
from vos.modelkit.verification import CheckResult, LinkVerification, VerificationReport
from vos.modelkit.vlan import VlanMetadata

__all__ = [
    # enums
    "CheckCategory",
    "CheckSeverity",
    "DeviceType",
    "PortType",
    "LinkType",
    "ObservationSource",
    "VlanMode",
    # device
    "Position",
    "Device",
    # port
    "VlanMembership",
    "ExpectedNeighbor",
    "Port",
    # link
    "LinkEndpoint",
    "Link",
    # vlan
    "VlanMetadata",
    # topology
    "TopologyMeta",
    "TopologySnapshot",
    # observation
    "Observation",
    "Mismatch",
    "MergeConflict",
    # verification
    "CheckResult",
    "LinkVerification",
    "VerificationReport",
    # trace
    "TraceRequest",
    "TraceHop",
    "BreakPoint",
    "TraceResult",
    # impact
    "ImpactRequest",
    "ImpactEffect",
    "ImpactResult",
    # explorer
    "Neighbor",
    "DanglingPort",
    "VlanPortEntry",
    "TopologyDiagnostics",
]
