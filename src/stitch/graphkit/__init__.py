"""graphkit — Graph traversal on topology snapshots.

Pure library. Neighbors, BFS/DFS, subgraph extraction, VLAN filtering.
Depends on: contractkit, modelkit. No spine dependency, no network I/O.
"""

from vos.graphkit.diagnostics import dangling_ports, diagnostics, missing_endpoints, orphan_devices
from vos.graphkit.neighbors import neighbors
from vos.graphkit.subgraph import subgraph
from vos.graphkit.traversal import bfs
from vos.graphkit.vlan import vlan_ports

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
