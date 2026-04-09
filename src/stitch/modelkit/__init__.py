from __future__ import annotations

from stitch.modelkit.device import Device, Position
from stitch.modelkit.enums import (
    CheckCategory,
    CheckSeverity,
    DeviceType,
    LinkType,
    ObservationSource,
    PortType,
    VlanMode,
)
from stitch.modelkit.explorer import DanglingPort, Neighbor, TopologyDiagnostics, VlanPortEntry
from stitch.modelkit.impact import ImpactEffect, ImpactRequest, ImpactResult
from stitch.modelkit.link import Link, LinkEndpoint
from stitch.modelkit.observation import MergeConflict, Mismatch, Observation
from stitch.modelkit.port import ExpectedNeighbor, Port, VlanMembership
from stitch.modelkit.topology import TopologyMeta, TopologySnapshot
from stitch.modelkit.trace import BreakPoint, TraceHop, TraceRequest, TraceResult
from stitch.modelkit.verification import CheckResult, LinkVerification, VerificationReport
from stitch.modelkit.vlan import VlanMetadata

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
