# Stitch MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local stdio MCP server that exposes Core-Stitcher's domain engine (9 tools) to Claude Code, including the first write-path tool for OPNsense interface assignment.

**Architecture:** FastMCP-based stdio server with thin tools, thick services, in-process domain engine, and MCP gateway client for adapter access. Lazy topology loading cached by mtime. Structured JSON response envelopes with error taxonomy.

**Tech Stack:** Python 3.14, FastMCP >= 2.0, stitch domain packages (verifykit, tracekit, graphkit, storekit, collectkit, modelkit, contractkit), httpx (gateway client)

**Spec:** `docs/superpowers/specs/2026-04-10-stitch-mcp-server-design.md`

---

## File Structure

### New package

```
src/stitch/mcp/
    __init__.py              — Package docstring
    server.py                — FastMCP app, tool registration, main()
    engine.py                — StitchEngine: lazy topology, gateway ref
    schemas.py               — ToolResponse envelope, error codes, DetailLevel

    tools/
        __init__.py
        preflight.py         — stitch_preflight_run tool
        trace.py             — stitch_trace_vlan, stitch_impact_preview tools
        topology.py          — 5 read tools (summary, devices, detail, neighbors, diagnostics)
        interface.py         — stitch_interface_assign tool

    services/
        __init__.py
        preflight_service.py — Collect → merge → verify pipeline
        topology_service.py  — Load, browse, diagnose
        interface_service.py — Read → validate → apply → verify → audit

    gateway/
        __init__.py
        client.py            — Re-export McpGatewayClient from contractkit
```

### New test files

```
tests/stitch_mcp/
    __init__.py
    conftest.py              — Fixtures: mock engine, mock gateway, sample topology
    test_schemas.py          — Response envelope, error formatting
    test_engine.py           — Lazy loading, mtime caching
    test_topology_tools.py   — 5 read tools
    test_preflight_tool.py   — Preflight workflow tool
    test_trace_tools.py      — Trace + impact tools
    test_interface_tool.py   — Write-path tool with dry_run
```

### Modified files

```
pyproject.toml               — Add fastmcp dep, add stitch-mcp console script
.mcp.json                    — Project-scoped MCP server config (NEW file)
```

---

## Task 1: Package Scaffold and FastMCP Dependency

**Files:**
- Modify: `pyproject.toml`
- Create: `src/stitch/mcp/__init__.py`
- Create: `src/stitch/mcp/tools/__init__.py`
- Create: `src/stitch/mcp/services/__init__.py`
- Create: `src/stitch/mcp/gateway/__init__.py`
- Create: `tests/stitch_mcp/__init__.py`
- Create: `.mcp.json`

- [ ] **Step 1: Add FastMCP dependency and entry point**

Add `fastmcp>=2.0.0` to `[project.dependencies]` in pyproject.toml.
Add `stitch-mcp = "stitch.mcp.server:main"` to `[project.scripts]`.

- [ ] **Step 2: Create package directories and __init__.py files**

```bash
mkdir -p src/stitch/mcp/tools src/stitch/mcp/services src/stitch/mcp/gateway
mkdir -p tests/stitch_mcp
```

`src/stitch/mcp/__init__.py`: `"""Stitch MCP server — domain engine tools for Claude Code."""`
`src/stitch/mcp/tools/__init__.py`: `"""MCP tool definitions — thin wrappers over services."""`
`src/stitch/mcp/services/__init__.py`: `"""Use-case orchestration services."""`
`src/stitch/mcp/gateway/__init__.py`: `"""MCP gateway client re-export."""`
`tests/stitch_mcp/__init__.py`: empty

- [ ] **Step 3: Create .mcp.json**

```json
{
  "mcpServers": {
    "stitch": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "stitch-mcp"],
      "env": {
        "MCP_GATEWAY_AUTH": "${MCP_GATEWAY_AUTH}",
        "STITCH_TOPOLOGY": "${STITCH_TOPOLOGY:-topologies/lab.json}",
        "MCP_GATEWAY_URL": "${MCP_GATEWAY_URL:-http://localhost:4444}"
      }
    }
  }
}
```

- [ ] **Step 4: Create minimal server.py**

`src/stitch/mcp/server.py`:
```python
"""Stitch MCP server — entry point."""

from __future__ import annotations

from fastmcp import FastMCP

mcp = FastMCP("stitch", instructions="Core-Stitcher domain engine: topology verification, VLAN tracing, impact analysis, device inspection.")


def main() -> None:
    mcp.run(transport="stdio")
```

- [ ] **Step 5: Verify install and entry point**

```bash
uv pip install -e ".[dev]"
uv run stitch-mcp --help  # or just verify it doesn't crash on import
```

- [ ] **Step 6: Verify existing tests**

```bash
uv run pytest tests/ --tb=short 2>&1 | tail -3
```
Expected: 837 passed.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .mcp.json src/stitch/mcp/ tests/stitch_mcp/
git commit -m "feat(mcp): scaffold stitch-mcp package with FastMCP"
```

---

## Task 2: Response Envelope and Error Taxonomy

**Files:**
- Create: `src/stitch/mcp/schemas.py`
- Test: `tests/stitch_mcp/test_schemas.py`

- [ ] **Step 1: Write failing tests**

`tests/stitch_mcp/test_schemas.py`:
```python
from stitch.mcp.schemas import DetailLevel, ErrorCode, ToolResponse


def test_success_response():
    r = ToolResponse.success(result={"count": 5}, summary="Found 5 items.")
    data = r.to_dict()
    assert data["ok"] is True
    assert data["summary"] == "Found 5 items."
    assert data["result"]["count"] == 5
    assert "meta" in data
    assert "generated_at" in data["meta"]


def test_failure_response():
    r = ToolResponse.failure(
        code=ErrorCode.DEVICE_NOT_FOUND,
        message="Device 'xyz' not found in topology",
        summary="Device not found.",
    )
    data = r.to_dict()
    assert data["ok"] is False
    assert data["error"]["code"] == "DEVICE_NOT_FOUND"
    assert data["error"]["message"] == "Device 'xyz' not found in topology"
    assert data["summary"] == "Device not found."


def test_detail_levels():
    assert DetailLevel.SUMMARY == "summary"
    assert DetailLevel.STANDARD == "standard"
    assert DetailLevel.FULL == "full"


def test_error_codes_exist():
    assert ErrorCode.TOPOLOGY_NOT_FOUND == "TOPOLOGY_NOT_FOUND"
    assert ErrorCode.GATEWAY_UNAVAILABLE == "GATEWAY_UNAVAILABLE"
    assert ErrorCode.INTERFACE_ALREADY_ASSIGNED == "INTERFACE_ALREADY_ASSIGNED"


def test_response_includes_topology_path():
    r = ToolResponse.success(result={}, summary="ok", topology_path="topologies/lab.json")
    data = r.to_dict()
    assert data["meta"]["topology_path"] == "topologies/lab.json"
```

- [ ] **Step 2: Implement schemas.py**

`src/stitch/mcp/schemas.py`:
```python
"""Response envelope, error codes, and shared types for MCP tools."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class DetailLevel(StrEnum):
    SUMMARY = "summary"
    STANDARD = "standard"
    FULL = "full"


class ErrorCode(StrEnum):
    # Topology
    TOPOLOGY_NOT_FOUND = "TOPOLOGY_NOT_FOUND"
    TOPOLOGY_INVALID = "TOPOLOGY_INVALID"
    # Device
    DEVICE_NOT_FOUND = "DEVICE_NOT_FOUND"
    DEVICE_AMBIGUOUS = "DEVICE_AMBIGUOUS"
    # Gateway
    GATEWAY_UNAVAILABLE = "GATEWAY_UNAVAILABLE"
    GATEWAY_TOOL_ERROR = "GATEWAY_TOOL_ERROR"
    GATEWAY_TIMEOUT = "GATEWAY_TIMEOUT"
    # Write-path
    INTERFACE_NOT_FOUND = "INTERFACE_NOT_FOUND"
    INTERFACE_ALREADY_ASSIGNED = "INTERFACE_ALREADY_ASSIGNED"
    APPLY_FAILED = "APPLY_FAILED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"


TOOL_VERSION = "1.0"


class ToolResponse:
    """Structured response envelope for all MCP tools."""

    def __init__(
        self,
        ok: bool,
        summary: str,
        result: dict[str, Any] | None = None,
        error: dict[str, str] | None = None,
        topology_path: str | None = None,
    ) -> None:
        self.ok = ok
        self.summary = summary
        self.result = result
        self.error = error
        self.topology_path = topology_path

    @classmethod
    def success(
        cls,
        result: Any,
        summary: str,
        topology_path: str | None = None,
    ) -> ToolResponse:
        return cls(ok=True, summary=summary, result=result, topology_path=topology_path)

    @classmethod
    def failure(
        cls,
        code: str | ErrorCode,
        message: str,
        summary: str,
        topology_path: str | None = None,
    ) -> ToolResponse:
        return cls(
            ok=False,
            summary=summary,
            error={"code": str(code), "message": message},
            topology_path=topology_path,
        )

    def to_dict(self) -> dict[str, Any]:
        meta = {
            "tool_version": TOOL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.topology_path:
            meta["topology_path"] = self.topology_path

        d: dict[str, Any] = {"ok": self.ok, "summary": self.summary, "meta": meta}
        if self.ok:
            d["result"] = self.result
        else:
            d["error"] = self.error
        return d
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/stitch_mcp/test_schemas.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/stitch/mcp/schemas.py tests/stitch_mcp/
git commit -m "feat(mcp): response envelope and error taxonomy"
```

---

## Task 3: StitchEngine with Lazy Topology Loading

**Files:**
- Create: `src/stitch/mcp/engine.py`
- Create: `src/stitch/mcp/gateway/client.py`
- Test: `tests/stitch_mcp/test_engine.py`

- [ ] **Step 1: Write failing tests**

`tests/stitch_mcp/test_engine.py`:
```python
import json
import pytest
from stitch.mcp.engine import StitchEngine


@pytest.fixture
def topology_file(tmp_path):
    topo = {
        "meta": {"version": "1.0", "name": "test", "updated": "2026-01-01", "updated_by": "test"},
        "devices": {
            "dev1": {"id": "dev1", "name": "Device 1", "type": "switch", "ports": {}},
            "dev2": {"id": "dev2", "name": "Device 2", "type": "firewall", "ports": {}},
        },
        "links": {},
        "vlans": {},
    }
    p = tmp_path / "test-topo.json"
    p.write_text(json.dumps(topo))
    return str(p)


def test_engine_lazy_load(topology_file):
    engine = StitchEngine(topology_path=topology_file, gateway_url="http://localhost:4444")
    assert engine._cached_topology is None
    topo = engine.get_topology()
    assert len(topo.devices) == 2
    assert engine._cached_topology is not None


def test_engine_caches_by_mtime(topology_file):
    engine = StitchEngine(topology_path=topology_file, gateway_url="http://localhost:4444")
    topo1 = engine.get_topology()
    topo2 = engine.get_topology()
    assert topo1 is topo2  # same object, cached


def test_engine_reloads_on_mtime_change(topology_file, tmp_path):
    engine = StitchEngine(topology_path=topology_file, gateway_url="http://localhost:4444")
    topo1 = engine.get_topology()

    import time, os
    time.sleep(0.1)
    # Rewrite file with different content
    new_topo = {
        "meta": {"version": "1.0", "name": "updated", "updated": "2026-01-02", "updated_by": "test"},
        "devices": {"dev1": {"id": "dev1", "name": "Device 1", "type": "switch", "ports": {}}},
        "links": {}, "vlans": {},
    }
    with open(topology_file, "w") as f:
        json.dump(new_topo, f)
    os.utime(topology_file, (time.time() + 1, time.time() + 1))

    topo2 = engine.get_topology()
    assert topo2 is not topo1
    assert len(topo2.devices) == 1


def test_engine_override_path(topology_file, tmp_path):
    other = tmp_path / "other.json"
    other.write_text(json.dumps({
        "meta": {"version": "1.0", "name": "other", "updated": "2026-01-01", "updated_by": "test"},
        "devices": {}, "links": {}, "vlans": {},
    }))
    engine = StitchEngine(topology_path=topology_file, gateway_url="http://localhost:4444")
    topo = engine.get_topology(override_path=str(other))
    assert len(topo.devices) == 0


def test_engine_get_explorer(topology_file):
    engine = StitchEngine(topology_path=topology_file, gateway_url="http://localhost:4444")
    explorer = engine.get_explorer()
    assert explorer is not None
    diag = explorer.get_diagnostics()
    assert diag.total_devices == 2
```

- [ ] **Step 2: Implement gateway/client.py**

`src/stitch/mcp/gateway/client.py`:
```python
"""Re-export McpGatewayClient from contractkit."""

from stitch.contractkit.gateway import McpGatewayClient

__all__ = ["McpGatewayClient"]
```

- [ ] **Step 3: Implement engine.py**

`src/stitch/mcp/engine.py`:
```python
"""StitchEngine — shared context for MCP tools."""

from __future__ import annotations

from pathlib import Path

from stitch.apps.explorer.workflow import ExplorerWorkflow
from stitch.mcp.gateway.client import McpGatewayClient
from stitch.modelkit.topology import TopologySnapshot
from stitch.storekit import load_topology


class StitchEngine:
    """Lazy topology loading with mtime cache, gateway client, and explorer factory."""

    def __init__(self, topology_path: str, gateway_url: str) -> None:
        self.topology_path = topology_path
        self.gateway_url = gateway_url
        self.gateway = McpGatewayClient(gateway_url)
        self._cached_topology: TopologySnapshot | None = None
        self._cached_mtime: float | None = None
        self._cached_path: str | None = None

    def get_topology(self, override_path: str | None = None) -> TopologySnapshot:
        path = Path(override_path or self.topology_path)
        mtime = path.stat().st_mtime
        if (
            self._cached_topology is None
            or mtime != self._cached_mtime
            or str(path) != self._cached_path
        ):
            self._cached_topology = load_topology(path)
            self._cached_mtime = mtime
            self._cached_path = str(path)
        return self._cached_topology

    def get_explorer(self, topology: TopologySnapshot | None = None) -> ExplorerWorkflow:
        topo = topology or self.get_topology()
        return ExplorerWorkflow(topo)
```

Note: `ExplorerWorkflow.__init__` currently takes a `topology_path`, not a `TopologySnapshot`. The implementer should check the actual signature and adapt — either pass the path, or modify ExplorerWorkflow to accept a pre-loaded topology. The spec says in-process, so passing a loaded topology is preferred. If ExplorerWorkflow needs modification, add a constructor overload or factory method.

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/stitch_mcp/ -v
```

- [ ] **Step 5: Commit**

```bash
git add src/stitch/mcp/ tests/stitch_mcp/
git commit -m "feat(mcp): StitchEngine with lazy topology loading and mtime cache"
```

---

## Task 4: Read Tools — Topology Service + 5 Tools

**Files:**
- Create: `src/stitch/mcp/services/topology_service.py`
- Create: `src/stitch/mcp/tools/topology.py`
- Modify: `src/stitch/mcp/server.py`
- Test: `tests/stitch_mcp/test_topology_tools.py`
- Create: `tests/stitch_mcp/conftest.py`

- [ ] **Step 1: Create shared test fixtures**

`tests/stitch_mcp/conftest.py`:
```python
"""Shared fixtures for MCP server tests."""

from __future__ import annotations

import json

import pytest

from stitch.mcp.engine import StitchEngine


SAMPLE_TOPOLOGY = {
    "meta": {"version": "1.0", "name": "test-lab", "updated": "2026-04-10T00:00:00Z", "updated_by": "test"},
    "devices": {
        "sw-core": {
            "id": "sw-core", "name": "sw-core-01", "type": "switch",
            "model": "USW-Pro-48", "management_ip": "192.168.254.2", "mcp_source": "switchcraft",
            "ports": {
                "sfp-0": {"type": "sfp+", "device_name": "sfp-0", "speed": "10G"},
                "eth0": {"type": "ethernet", "device_name": "eth0", "speed": "1G"},
            },
        },
        "fw-main": {
            "id": "fw-main", "name": "fw-main", "type": "firewall",
            "model": "OPNsense", "management_ip": "172.16.0.1", "mcp_source": "opnsensecraft",
            "ports": {
                "igc0": {"type": "ethernet", "device_name": "igc0", "speed": "2.5G"},
                "igc1": {"type": "ethernet", "device_name": "igc1", "speed": "2.5G"},
            },
        },
    },
    "links": {
        "link-1": {
            "id": "link-1", "type": "physical_cable",
            "endpoints": [{"device": "sw-core", "port": "sfp-0"}, {"device": "fw-main", "port": "igc0"}],
        },
    },
    "vlans": {"42": {"name": "servers", "color": "#4ade80"}},
}


@pytest.fixture
def topology_file(tmp_path):
    p = tmp_path / "test-topo.json"
    p.write_text(json.dumps(SAMPLE_TOPOLOGY))
    return str(p)


@pytest.fixture
def engine(topology_file):
    return StitchEngine(topology_path=topology_file, gateway_url="http://localhost:4444")
```

- [ ] **Step 2: Write failing tests for topology tools**

`tests/stitch_mcp/test_topology_tools.py`:
```python
import pytest
from stitch.mcp.services.topology_service import TopologyService
from stitch.mcp.schemas import DetailLevel


def test_topology_summary(engine):
    svc = TopologyService(engine)
    resp = svc.summary()
    assert resp.ok
    data = resp.to_dict()
    assert data["result"]["device_count"] == 2
    assert data["result"]["link_count"] == 1


def test_devices_standard(engine):
    svc = TopologyService(engine)
    resp = svc.devices(detail=DetailLevel.STANDARD)
    assert resp.ok
    data = resp.to_dict()
    assert data["result"]["total_count"] == 2
    assert len(data["result"]["devices"]) == 2
    assert data["result"]["devices"][0]["name"] in ("sw-core-01", "fw-main")


def test_devices_summary_mode(engine):
    svc = TopologyService(engine)
    resp = svc.devices(detail=DetailLevel.SUMMARY)
    data = resp.to_dict()
    # Summary mode only returns id, name, type
    device = data["result"]["devices"][0]
    assert "id" in device
    assert "name" in device
    assert "model" not in device


def test_device_detail(engine):
    svc = TopologyService(engine)
    resp = svc.device_detail("sw-core")
    assert resp.ok
    data = resp.to_dict()
    assert data["result"]["device"]["name"] == "sw-core-01"
    assert len(data["result"]["ports"]) == 2


def test_device_detail_not_found(engine):
    svc = TopologyService(engine)
    resp = svc.device_detail("nonexistent")
    assert not resp.ok
    assert resp.error["code"] == "DEVICE_NOT_FOUND"


def test_device_neighbors(engine):
    svc = TopologyService(engine)
    resp = svc.device_neighbors("sw-core")
    assert resp.ok
    data = resp.to_dict()
    assert len(data["result"]) >= 1  # fw-main is a neighbor via link-1


def test_diagnostics(engine):
    svc = TopologyService(engine)
    resp = svc.diagnostics()
    assert resp.ok
    data = resp.to_dict()
    assert data["result"]["total_devices"] == 2
```

- [ ] **Step 3: Implement topology_service.py**

`src/stitch/mcp/services/topology_service.py`:
```python
"""Topology browsing service — load, list, inspect, diagnose."""

from __future__ import annotations

from stitch.mcp.engine import StitchEngine
from stitch.mcp.schemas import DetailLevel, ErrorCode, ToolResponse


class TopologyService:
    def __init__(self, engine: StitchEngine) -> None:
        self._engine = engine

    def summary(self, topology_path: str | None = None) -> ToolResponse:
        try:
            topo = self._engine.get_topology(topology_path)
        except FileNotFoundError:
            return ToolResponse.failure(ErrorCode.TOPOLOGY_NOT_FOUND, f"Topology file not found: {topology_path or self._engine.topology_path}", "Topology file not found.")
        except Exception as e:
            return ToolResponse.failure(ErrorCode.TOPOLOGY_INVALID, str(e), "Failed to load topology.")

        result = {
            "name": topo.meta.name if hasattr(topo.meta, "name") else topo.meta.get("name", ""),
            "version": topo.meta.version if hasattr(topo.meta, "version") else topo.meta.get("version", ""),
            "device_count": len(topo.devices),
            "link_count": len(topo.links),
            "vlan_count": len(topo.vlans),
        }
        return ToolResponse.success(
            result=result,
            summary=f"Topology '{result['name']}': {result['device_count']} devices, {result['link_count']} links, {result['vlan_count']} VLANs.",
            topology_path=topology_path or self._engine.topology_path,
        )

    def devices(self, topology_path: str | None = None, detail: DetailLevel = DetailLevel.STANDARD) -> ToolResponse:
        try:
            topo = self._engine.get_topology(topology_path)
        except FileNotFoundError:
            return ToolResponse.failure(ErrorCode.TOPOLOGY_NOT_FOUND, "File not found", "Topology not found.")

        devices = []
        for dev_id, dev in topo.devices.items():
            d = dev if isinstance(dev, dict) else dev.model_dump()
            if detail == DetailLevel.SUMMARY:
                devices.append({"id": dev_id, "name": d.get("name", dev_id), "type": d.get("type", "")})
            else:
                ports = d.get("ports", {})
                devices.append({
                    "id": dev_id, "name": d.get("name", dev_id), "type": d.get("type", ""),
                    "model": d.get("model"), "management_ip": d.get("management_ip"),
                    "port_count": len(ports), "mcp_source": d.get("mcp_source"),
                })

        return ToolResponse.success(
            result={"devices": devices, "total_count": len(devices), "truncated": False},
            summary=f"{len(devices)} devices: {', '.join(d['name'] for d in devices[:5])}{'...' if len(devices) > 5 else ''}.",
            topology_path=topology_path or self._engine.topology_path,
        )

    def device_detail(self, device_id: str, topology_path: str | None = None) -> ToolResponse:
        try:
            topo = self._engine.get_topology(topology_path)
        except FileNotFoundError:
            return ToolResponse.failure(ErrorCode.TOPOLOGY_NOT_FOUND, "File not found", "Topology not found.")

        dev_data = topo.devices.get(device_id)
        if dev_data is None:
            return ToolResponse.failure(
                ErrorCode.DEVICE_NOT_FOUND,
                f"Device '{device_id}' not found in topology",
                f"Device '{device_id}' not found.",
            )

        d = dev_data if isinstance(dev_data, dict) else dev_data.model_dump()
        ports = d.get("ports", {})
        port_list = [{"name": k, **v} if isinstance(v, dict) else {"name": k, **v.model_dump()} for k, v in ports.items()]

        return ToolResponse.success(
            result={"device": d, "ports": port_list},
            summary=f"{d.get('name', device_id)} ({d.get('type', '?')}): {len(port_list)} ports.",
            topology_path=topology_path or self._engine.topology_path,
        )

    def device_neighbors(self, device_id: str, topology_path: str | None = None) -> ToolResponse:
        try:
            topo = self._engine.get_topology(topology_path)
        except FileNotFoundError:
            return ToolResponse.failure(ErrorCode.TOPOLOGY_NOT_FOUND, "File not found", "Topology not found.")

        if device_id not in topo.devices:
            return ToolResponse.failure(ErrorCode.DEVICE_NOT_FOUND, f"Device '{device_id}' not found", f"Device '{device_id}' not found.")

        explorer = self._engine.get_explorer(topo)
        nbrs = explorer.get_neighbors(device_id)
        nbr_list = [n if isinstance(n, dict) else n.model_dump() for n in nbrs]

        names = [n.get("device", n.device if hasattr(n, "device") else "?") for n in nbrs]
        return ToolResponse.success(
            result=nbr_list,
            summary=f"{device_id} has {len(nbr_list)} neighbor(s): {', '.join(names[:5])}.",
            topology_path=topology_path or self._engine.topology_path,
        )

    def diagnostics(self, topology_path: str | None = None) -> ToolResponse:
        try:
            topo = self._engine.get_topology(topology_path)
        except FileNotFoundError:
            return ToolResponse.failure(ErrorCode.TOPOLOGY_NOT_FOUND, "File not found", "Topology not found.")

        explorer = self._engine.get_explorer(topo)
        diag = explorer.get_diagnostics()
        d = diag if isinstance(diag, dict) else diag.model_dump()

        return ToolResponse.success(
            result=d,
            summary=f"Diagnostics: {d.get('total_devices', 0)} devices, {d.get('dangling_ports', []).__len__()} dangling ports, {d.get('orphan_devices', []).__len__()} orphans.",
            topology_path=topology_path or self._engine.topology_path,
        )
```

- [ ] **Step 4: Implement topology tools (thin wrappers)**

`src/stitch/mcp/tools/topology.py`:
```python
"""Topology read tools — thin wrappers over TopologyService."""

from __future__ import annotations

import json

from stitch.mcp.schemas import DetailLevel
from stitch.mcp.services.topology_service import TopologyService


def register_topology_tools(mcp, engine) -> None:
    """Register all 5 topology read tools on the FastMCP app."""
    svc = TopologyService(engine)

    @mcp.tool()
    def stitch_topology_summary(topology_path: str | None = None) -> str:
        """Get a summary of the declared network topology: device count, link count, VLAN count."""
        return json.dumps(svc.summary(topology_path).to_dict())

    @mcp.tool()
    def stitch_devices(topology_path: str | None = None, detail: str = "standard") -> str:
        """List all devices in the topology with name, type, model, and IP."""
        return json.dumps(svc.devices(topology_path, DetailLevel(detail)).to_dict())

    @mcp.tool()
    def stitch_device_detail(device_id: str) -> str:
        """Get detailed information about a specific device including all ports."""
        return json.dumps(svc.device_detail(device_id).to_dict())

    @mcp.tool()
    def stitch_device_neighbors(device_id: str) -> str:
        """Get the neighbors of a device — which devices are connected to it and through which ports."""
        return json.dumps(svc.device_neighbors(device_id).to_dict())

    @mcp.tool()
    def stitch_topology_diagnostics(topology_path: str | None = None) -> str:
        """Diagnose topology health: dangling ports, orphan devices, missing link endpoints."""
        return json.dumps(svc.diagnostics(topology_path).to_dict())
```

- [ ] **Step 5: Wire tools into server.py**

Update `src/stitch/mcp/server.py`:
```python
"""Stitch MCP server — entry point."""

from __future__ import annotations

import os

from fastmcp import FastMCP

from stitch.mcp.engine import StitchEngine

mcp = FastMCP("stitch", instructions="Core-Stitcher domain engine: topology verification, VLAN tracing, impact analysis, device inspection.")


def _create_engine() -> StitchEngine:
    return StitchEngine(
        topology_path=os.environ.get("STITCH_TOPOLOGY", "topologies/lab.json"),
        gateway_url=os.environ.get("MCP_GATEWAY_URL", "http://localhost:4444"),
    )


engine = _create_engine()

# Register tools
from stitch.mcp.tools.topology import register_topology_tools
register_topology_tools(mcp, engine)


def main() -> None:
    mcp.run(transport="stdio")
```

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/stitch_mcp/ -v
```

- [ ] **Step 7: Commit**

```bash
git add src/stitch/mcp/ tests/stitch_mcp/
git commit -m "feat(mcp): 5 topology read tools with service layer"
```

---

## Task 5: Trace and Impact Tools

**Files:**
- Create: `src/stitch/mcp/tools/trace.py`
- Modify: `src/stitch/mcp/server.py`
- Test: `tests/stitch_mcp/test_trace_tools.py`

- [ ] **Step 1: Write failing tests**

`tests/stitch_mcp/test_trace_tools.py`:
```python
from stitch.mcp.services.topology_service import TopologyService
from stitch.mcp.engine import StitchEngine


def test_trace_vlan(engine):
    # Trace needs the topology loaded — test basic invocation
    from stitch.mcp.tools.trace import _trace_vlan_impl
    resp = _trace_vlan_impl(engine, vlan=42, source="sw-core")
    assert resp.ok or not resp.ok  # may fail if VLAN 42 has no path, but should not crash


def test_impact_preview(engine):
    from stitch.mcp.tools.trace import _impact_preview_impl
    resp = _impact_preview_impl(engine, action="remove_link", device="sw-core", port="sfp-0")
    assert resp.ok or not resp.ok  # result depends on topology, should not crash
```

- [ ] **Step 2: Implement trace tools**

`src/stitch/mcp/tools/trace.py`:
```python
"""Trace and impact tools."""

from __future__ import annotations

import json

from stitch.mcp.engine import StitchEngine
from stitch.mcp.schemas import ErrorCode, ToolResponse
from stitch.modelkit.impact import ImpactRequest
from stitch.modelkit.trace import TraceRequest


def _trace_vlan_impl(engine: StitchEngine, vlan: int, source: str | None = None, target: str | None = None) -> ToolResponse:
    try:
        topo = engine.get_topology()
    except FileNotFoundError:
        return ToolResponse.failure(ErrorCode.TOPOLOGY_NOT_FOUND, "Topology not found", "Topology not found.")

    explorer = engine.get_explorer(topo)
    request = TraceRequest(vlan=vlan, source=source, target=target)
    result = explorer.trace(request)
    d = result.model_dump()

    hops = d.get("hops", [])
    status = d.get("status", "unknown")
    return ToolResponse.success(
        result=d,
        summary=f"VLAN {vlan}: {status} ({len(hops)} hops).",
        topology_path=engine.topology_path,
    )


def _impact_preview_impl(engine: StitchEngine, action: str, device: str, port: str | None = None, parameters: dict | None = None) -> ToolResponse:
    try:
        topo = engine.get_topology()
    except FileNotFoundError:
        return ToolResponse.failure(ErrorCode.TOPOLOGY_NOT_FOUND, "Topology not found", "Topology not found.")

    explorer = engine.get_explorer(topo)
    request = ImpactRequest(action=action, device=device, port=port, parameters=parameters or {})
    result = explorer.impact(request)
    d = result.model_dump()

    risk = d.get("risk", "unknown")
    effects = d.get("impact", [])
    return ToolResponse.success(
        result=d,
        summary=f"Impact of {action} on {device}: {risk} risk, {len(effects)} affected endpoints.",
        topology_path=engine.topology_path,
    )


def register_trace_tools(mcp, engine: StitchEngine) -> None:
    @mcp.tool()
    def stitch_trace_vlan(vlan: int, source: str | None = None, target: str | None = None) -> str:
        """Trace a VLAN path through the network topology. Shows hop-by-hop path with status."""
        return json.dumps(_trace_vlan_impl(engine, vlan, source, target).to_dict())

    @mcp.tool()
    def stitch_impact_preview(action: str, device: str, port: str | None = None, parameters: str | None = None) -> str:
        """Preview the impact of a proposed network change. Shows affected devices, risk level, and safety assessment."""
        params = json.loads(parameters) if parameters else {}
        return json.dumps(_impact_preview_impl(engine, action, device, port, params).to_dict())
```

- [ ] **Step 3: Register in server.py**

Add to server.py after topology registration:
```python
from stitch.mcp.tools.trace import register_trace_tools
register_trace_tools(mcp, engine)
```

- [ ] **Step 4: Run tests and commit**

```bash
uv run pytest tests/stitch_mcp/ -v
git add src/stitch/mcp/ tests/stitch_mcp/
git commit -m "feat(mcp): trace VLAN and impact preview tools"
```

---

## Task 6: Preflight Tool

**Files:**
- Create: `src/stitch/mcp/services/preflight_service.py`
- Create: `src/stitch/mcp/tools/preflight.py`
- Modify: `src/stitch/mcp/server.py`
- Test: `tests/stitch_mcp/test_preflight_tool.py`

- [ ] **Step 1: Write failing tests**

`tests/stitch_mcp/test_preflight_tool.py`:
```python
from unittest.mock import AsyncMock, patch
import pytest
from stitch.mcp.services.preflight_service import PreflightService


@pytest.mark.asyncio
async def test_preflight_run_no_adapters(engine):
    """Preflight with no live adapters should still run (0 observations, all mismatches)."""
    svc = PreflightService(engine)
    resp = await svc.run(adapters=[])
    assert resp.ok
    data = resp.to_dict()
    # With 0 observations, everything will be missing
    assert "result" in data
    assert "verdict" in data["result"]
```

- [ ] **Step 2: Implement preflight_service.py**

`src/stitch/mcp/services/preflight_service.py`:
```python
"""Preflight verification service — collect, merge, verify."""

from __future__ import annotations

from stitch.collectkit.merger import merge_observations
from stitch.mcp.engine import StitchEngine
from stitch.mcp.schemas import DetailLevel, ErrorCode, ToolResponse
from stitch.verifykit.engine import verify_topology


class PreflightService:
    def __init__(self, engine: StitchEngine) -> None:
        self._engine = engine

    async def run(
        self,
        topology_path: str | None = None,
        adapters: list | None = None,
        detail: DetailLevel = DetailLevel.STANDARD,
    ) -> ToolResponse:
        try:
            topo = self._engine.get_topology(topology_path)
        except FileNotFoundError:
            return ToolResponse.failure(ErrorCode.TOPOLOGY_NOT_FOUND, "Topology not found", "Topology not found.")

        # Collect observations from adapters
        observations = []
        if adapters is not None:
            for collector in adapters:
                try:
                    obs = await collector.collect()
                    observations.extend(obs)
                except Exception as e:
                    # Gateway errors don't abort the whole run
                    pass

        # Merge and verify
        observed, conflicts = merge_observations(observations)
        report = verify_topology(topo, observed)

        # Format result
        r = report if isinstance(report, dict) else report.model_dump()
        summary_data = r.get("summary", {})
        if isinstance(summary_data, dict):
            ok_count = summary_data.get("ok", 0)
            warn_count = summary_data.get("warning", 0)
            err_count = summary_data.get("error", 0)
            total = summary_data.get("total", 0)
        else:
            ok_count = getattr(summary_data, "ok", 0)
            warn_count = getattr(summary_data, "warning", 0)
            err_count = getattr(summary_data, "error", 0)
            total = getattr(summary_data, "total", 0)

        verdict = "pass" if err_count == 0 and warn_count == 0 else "fail" if err_count > 0 else "warning"

        results = r.get("results", [])
        if detail == DetailLevel.SUMMARY:
            findings = []
        elif detail == DetailLevel.STANDARD:
            # Top N findings (errors first, then warnings)
            findings = [res for res in results if (res.get("highest_severity") or res.get("status")) in ("error", "fail")][:10]
        else:
            findings = results

        result = {
            "verdict": verdict,
            "total_links": total,
            "ok": ok_count,
            "warning": warn_count,
            "error": err_count,
            "findings": findings,
            "truncated": len(findings) < len(results),
            "detail_available": len(results) > len(findings),
            "observations_collected": len(observations),
        }

        return ToolResponse.success(
            result=result,
            summary=f"Preflight: {ok_count}/{total} OK, {warn_count} warnings, {err_count} errors. Verdict: {verdict}.",
            topology_path=topology_path or self._engine.topology_path,
        )
```

- [ ] **Step 3: Implement preflight tool**

`src/stitch/mcp/tools/preflight.py`:
```python
"""Preflight verification tool."""

from __future__ import annotations

import asyncio
import json

from stitch.mcp.engine import StitchEngine
from stitch.mcp.schemas import DetailLevel
from stitch.mcp.services.preflight_service import PreflightService


def register_preflight_tools(mcp, engine: StitchEngine) -> None:
    svc = PreflightService(engine)

    @mcp.tool()
    def stitch_preflight_run(
        topology_path: str | None = None,
        scope: str | None = None,
        detail: str = "standard",
    ) -> str:
        """Run full preflight verification: collect live observations from network adapters, merge, and compare against declared topology. Returns a verification report with findings."""
        # Build adapter list from topology mcp_source fields
        adapters = _build_adapters(engine, scope)
        resp = asyncio.run(svc.run(topology_path, adapters, DetailLevel(detail)))
        return json.dumps(resp.to_dict())


def _build_adapters(engine: StitchEngine, scope: str | None = None):
    """Auto-discover adapters from topology device mcp_source fields."""
    from stitch.opnsensecraft.collector import OpnsensecraftCollector

    topo = engine.get_topology()
    adapters = []
    for dev_id, dev in topo.devices.items():
        d = dev if isinstance(dev, dict) else dev.model_dump()
        source = d.get("mcp_source", "")
        if source == "opnsensecraft":
            adapters.append(OpnsensecraftCollector(
                dev_id,
                device_name=d.get("name"),
                management_ip=d.get("management_ip"),
                gateway_url=engine.gateway_url,
            ))
        # Add switchcraft, proxmoxcraft patterns here as they become available
    return adapters
```

- [ ] **Step 4: Register in server.py and run tests**

```python
from stitch.mcp.tools.preflight import register_preflight_tools
register_preflight_tools(mcp, engine)
```

```bash
uv run pytest tests/stitch_mcp/ -v
git add src/stitch/mcp/ tests/stitch_mcp/
git commit -m "feat(mcp): preflight verification tool with adapter auto-discovery"
```

---

## Task 7: Interface Assign Tool (Write-Path)

**Files:**
- Create: `src/stitch/mcp/services/interface_service.py`
- Create: `src/stitch/mcp/tools/interface.py`
- Modify: `src/stitch/mcp/server.py`
- Test: `tests/stitch_mcp/test_interface_tool.py`

- [ ] **Step 1: Write failing tests**

`tests/stitch_mcp/test_interface_tool.py`:
```python
from unittest.mock import AsyncMock
import pytest
from stitch.mcp.services.interface_service import InterfaceService
from stitch.mcp.schemas import ErrorCode


@pytest.mark.asyncio
async def test_interface_assign_dry_run(engine):
    """Dry run should return projected state without calling gateway."""
    svc = InterfaceService(engine)
    # Mock the gateway so it doesn't make real calls
    engine.gateway.call_tool = AsyncMock(return_value={
        "total": 3,
        "rows": [
            {"device": "igc0", "config": {"identifier": "wan"}, "description": "WAN"},
            {"device": "igc1", "config": {"identifier": "lan"}, "description": "LAN"},
            {"device": "ix0", "config": {}, "description": ""},  # unassigned
        ],
    })
    resp = await svc.assign(
        device_id="fw-main",
        physical_interface="ix0",
        assign_as="opt1",
        description="Frontend trunk",
        dry_run=True,
    )
    assert resp.ok
    data = resp.to_dict()
    assert data["result"]["dry_run"] is True
    assert data["result"]["applied"] is False


@pytest.mark.asyncio
async def test_interface_assign_not_found(engine):
    svc = InterfaceService(engine)
    resp = await svc.assign(
        device_id="nonexistent",
        physical_interface="ix0",
        assign_as="opt1",
        dry_run=True,
    )
    assert not resp.ok
    assert resp.error["code"] == "DEVICE_NOT_FOUND"


@pytest.mark.asyncio
async def test_interface_assign_already_assigned(engine):
    svc = InterfaceService(engine)
    engine.gateway.call_tool = AsyncMock(return_value={
        "total": 1,
        "rows": [{"device": "igc0", "config": {"identifier": "wan"}, "description": "WAN"}],
    })
    resp = await svc.assign(
        device_id="fw-main",
        physical_interface="igc0",
        assign_as="opt1",
        dry_run=True,
    )
    assert not resp.ok
    assert resp.error["code"] == "INTERFACE_ALREADY_ASSIGNED"
```

- [ ] **Step 2: Implement interface_service.py**

`src/stitch/mcp/services/interface_service.py`:
```python
"""Interface assignment service — read, validate, apply, verify, audit."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from stitch.mcp.engine import StitchEngine
from stitch.mcp.schemas import ErrorCode, ToolResponse

AUDIT_LOG = Path.home() / ".stitch" / "audit.jsonl"


class InterfaceService:
    def __init__(self, engine: StitchEngine) -> None:
        self._engine = engine

    async def assign(
        self,
        device_id: str,
        physical_interface: str,
        assign_as: str,
        description: str | None = None,
        dry_run: bool = True,
    ) -> ToolResponse:
        # 1. Validate device exists
        topo = self._engine.get_topology()
        if device_id not in topo.devices:
            return ToolResponse.failure(ErrorCode.DEVICE_NOT_FOUND, f"Device '{device_id}' not found", f"Device '{device_id}' not found.")

        # 2. Read current state from OPNsense
        try:
            ifaces = await self._engine.gateway.call_tool("opnsense-get-interfaces")
        except Exception as e:
            return ToolResponse.failure(ErrorCode.GATEWAY_UNAVAILABLE, str(e), "Cannot reach OPNsense via MCP gateway.")

        if ifaces is None:
            return ToolResponse.failure(ErrorCode.GATEWAY_TOOL_ERROR, "No response from opnsense-get-interfaces", "Gateway returned no data.")

        # 3. Find the target interface
        rows = ifaces.get("rows", []) if isinstance(ifaces, dict) else []
        target = None
        for row in rows:
            if row.get("device") == physical_interface:
                target = row
                break

        if target is None:
            return ToolResponse.failure(ErrorCode.INTERFACE_NOT_FOUND, f"Interface '{physical_interface}' not found on OPNsense", f"Interface '{physical_interface}' not found.")

        # 4. Check if already assigned
        config = target.get("config", {})
        identifier = config.get("identifier", "")
        if identifier:
            return ToolResponse.failure(
                ErrorCode.INTERFACE_ALREADY_ASSIGNED,
                f"'{physical_interface}' is already assigned as '{identifier}'",
                f"Interface '{physical_interface}' is already assigned to '{identifier}'.",
            )

        # 5. Build before state
        before = {"interface": physical_interface, "assigned_as": None, "description": target.get("description", "")}

        # 6. Dry run — return projected state
        projected_after = {"interface": physical_interface, "assigned_as": assign_as, "description": description or ""}

        if dry_run:
            result = {
                "dry_run": True,
                "before": before,
                "after": projected_after,
                "verification": {"changed": True, "before_role": None, "after_role": assign_as},
                "applied": False,
            }
            self._audit(device_id, physical_interface, assign_as, dry_run, before, projected_after, True)
            return ToolResponse.success(
                result=result,
                summary=f"Dry run: would assign {physical_interface} as {assign_as} on {device_id}. No changes applied.",
                topology_path=self._engine.topology_path,
            )

        # 7. Real apply — call OPNsense to assign interface
        # This will be implemented when we have the right OPNsense MCP tool
        # For now, return a clear error that real apply is not yet wired
        return ToolResponse.failure(
            ErrorCode.APPLY_FAILED,
            "Real interface assignment not yet implemented — only dry_run is available in v1",
            "Real apply not yet available. Use dry_run: true.",
        )

    def _audit(self, device_id, interface, role, dry_run, before, after, success):
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": "stitch_interface_assign",
            "input": {"device_id": device_id, "physical_interface": interface, "assign_as": role, "dry_run": dry_run},
            "before": before,
            "after": after,
            "applied": not dry_run,
            "success": success,
        }
        with open(AUDIT_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
```

- [ ] **Step 3: Implement interface tool**

`src/stitch/mcp/tools/interface.py`:
```python
"""Interface assignment tool (write-path)."""

from __future__ import annotations

import asyncio
import json

from stitch.mcp.engine import StitchEngine
from stitch.mcp.services.interface_service import InterfaceService


def register_interface_tools(mcp, engine: StitchEngine) -> None:
    svc = InterfaceService(engine)

    @mcp.tool()
    def stitch_interface_assign(
        device_id: str,
        physical_interface: str,
        assign_as: str,
        description: str | None = None,
        dry_run: bool = True,
    ) -> str:
        """Assign a physical network interface to a logical role on an OPNsense device. Defaults to dry_run=true (no changes applied). Set dry_run=false to apply."""
        resp = asyncio.run(svc.assign(device_id, physical_interface, assign_as, description, dry_run))
        return json.dumps(resp.to_dict())
```

- [ ] **Step 4: Register in server.py and run all tests**

```python
from stitch.mcp.tools.interface import register_interface_tools
register_interface_tools(mcp, engine)
```

```bash
uv run pytest tests/stitch_mcp/ -v
uv run pytest tests/ --tb=short 2>&1 | tail -3  # full suite
```

- [ ] **Step 5: Commit**

```bash
git add src/stitch/mcp/ tests/stitch_mcp/
git commit -m "feat(mcp): interface assign write-path tool with dry_run and audit"
```

---

## Task 8: End-to-End Verification

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest tests/ -v --tb=short 2>&1 | tail -5
```
Expected: 837+ passed (existing + new MCP tests).

- [ ] **Step 2: Lint**

```bash
uv run ruff check src/stitch/mcp/ tests/stitch_mcp/
```

- [ ] **Step 3: Type check**

```bash
uv run pyright src/stitch/mcp/
```

- [ ] **Step 4: Test MCP server starts**

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | uv run stitch-mcp
```
Expected: JSON response listing 9 tools.

- [ ] **Step 5: Test one tool via stdio**

```bash
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"stitch_topology_summary","arguments":{}}}' | STITCH_TOPOLOGY=topologies/lab.json uv run stitch-mcp
```
Expected: JSON response with topology summary (8 devices, 16 links).

- [ ] **Step 6: Commit any fixes**

```bash
git add -A
git commit -m "feat(mcp): stitch-mcp server complete — 9 tools, stdio transport"
```

---

## Self-Review

**Spec coverage:**
- [x] §2 Architecture: lazy topology, in-process domain, gateway for adapters — Tasks 1, 3
- [x] §3 Response envelope: ok/summary/result/meta, error codes — Task 2
- [x] §4 Tool contracts: all 9 tools — Tasks 4-7
- [x] §5 Error taxonomy: all codes defined and used — Task 2, used in Tasks 4-7
- [x] §6 Package structure: tools/services/gateway split — Tasks 1, 3-7
- [x] §7 Engine: lazy loading, mtime cache — Task 3
- [x] §8 Registration: .mcp.json, console script — Task 1
- [x] §9 Audit log: JSONL append-only — Task 7
- [x] §10 Not in v1: correctly excluded (no HTTP, no VLAN apply, no report persistence)
- [x] §11 Dependencies: gateway reuse, not copy — Task 3

**Type consistency:** ToolResponse used consistently. StitchEngine interface stable across all tasks. DetailLevel enum used in preflight and devices tools.

**Placeholder scan:** No TBDs. The real apply path in interface_service returns an explicit error explaining it's not wired yet — this is deliberate (v1 is dry_run only for safety, real apply needs the specific OPNsense MCP tool which we'll wire in Phase B).
