"""StitchEngine — shared engine context with lazy topology loading."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from stitch.apps.explorer.workflow import ExplorerWorkflow
from stitch.mcp.gateway.client import McpGatewayClient
from stitch.storekit import load_topology

if TYPE_CHECKING:
    from pathlib import Path

    from stitch.modelkit.topology import TopologySnapshot


class StitchEngine:
    """Shared context for MCP tools: gateway client + lazy-cached topology."""

    def __init__(self, topology_path: str | Path, gateway_url: str) -> None:
        self.topology_path = str(topology_path)
        self.gateway_url = gateway_url
        self.gateway = McpGatewayClient(gateway_url=gateway_url)
        self._cached_topology: TopologySnapshot | None = None
        self._cached_mtime: float | None = None
        self._cached_path: str | None = None

    def get_topology(self, *, override_path: str | None = None) -> TopologySnapshot:
        """Load topology, caching by (path, mtime). Reloads if file changed."""
        path = override_path or self.topology_path
        mtime = os.path.getmtime(path)

        if (
            self._cached_topology is not None
            and self._cached_path == path
            and self._cached_mtime == mtime
        ):
            return self._cached_topology

        topo = load_topology(path)
        self._cached_topology = topo
        self._cached_mtime = mtime
        self._cached_path = path
        return topo

    def get_explorer(self, *, topology_path: str | None = None) -> ExplorerWorkflow:
        """Create an ExplorerWorkflow for the given (or default) topology path."""
        path = topology_path or self.topology_path
        return ExplorerWorkflow(topology_path=path)
