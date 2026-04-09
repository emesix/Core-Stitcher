"""graphkit — Graph traversal on topology snapshots.

Pure library. Neighbors, BFS/DFS, subgraph extraction, VLAN filtering.
Depends on: contractkit, modelkit. No spine dependency, no network I/O.
"""

from stitch.graphkit.diagnostics import (
    dangling_ports,
    diagnostics,
    missing_endpoints,
    orphan_devices,
)
from stitch.graphkit.neighbors import neighbors
from stitch.graphkit.subgraph import subgraph
from stitch.graphkit.traversal import bfs
from stitch.graphkit.vlan import vlan_ports

__all__ = [
    "bfs",
    "dangling_ports",
    "diagnostics",
    "missing_endpoints",
    "neighbors",
    "orphan_devices",
    "subgraph",
    "vlan_ports",
]
