"""storekit — Topology snapshot serialization, schema versioning, diff.

Pure library. Load/save topology.json, schema migration, import/export, diffing.
Depends on: contractkit, modelkit. No spine dependency, no network I/O
(local file I/O for topology snapshots by design — no DB, no MCP).
"""

from vos.storekit.loader import load_topology, save_topology

__all__ = ["load_topology", "save_topology"]
