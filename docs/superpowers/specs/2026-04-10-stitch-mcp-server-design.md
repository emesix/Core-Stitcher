# Stitch MCP Server Design

**Date:** 2026-04-10
**Status:** Approved for implementation
**Scope:** Core-Stitcher MCP server exposing domain engine to Claude Code via stdio, plus first write-path tool

---

## 1. Purpose

Expose Core-Stitcher's domain engine (verification, tracing, impact analysis, topology browsing) as MCP tools that Claude Code can call directly. This makes Claude Code the primary operator interface while Core-Stitcher remains the deterministic domain engine.

**One-line summary:** Claude Code asks questions and takes actions; stitch-mcp runs the verified logic.

---

## 2. Architecture

```
Claude Code (stdio)
    │
    ▼
stitch-mcp (Python, FastMCP, stdio transport)
    │
    ├── Tools layer (thin: input parsing, envelope formatting, tool registration)
    │
    ├── Services layer (use-case orchestration)
    │   ├── preflight_service   — collect → merge → verify pipeline
    │   ├── topology_service    — load, browse, diagnose
    │   └── interface_service   — read → validate → apply → verify
    │
    ├── Engine (shared context)
    │   ├── Lazy topology loading (cached by path + mtime)
    │   ├── ExplorerWorkflow (in-process, no HTTP)
    │   └── Gateway client reference
    │
    └── Gateway client (HTTP to localhost:4444)
        └── McpGatewayClient for adapter tools (opnsense-*, switchcraft-*)
```

**Key decisions:**

- **Domain engine runs in-process.** Verification, tracing, impact analysis call Python functions directly. No HTTP round-trip for read operations.
- **Gateway client only for adapter operations.** Collecting live observations and write-path changes go through the MCP gateway to reach opnsense/switchcraft/proxmox tools.
- **Topology loaded lazily, cached by mtime.** No eager loading at startup. Every tool call gets a fresh view if the file changed. No mutable observed state across calls.
- **Transport-agnostic core.** Stdio now, HTTP transport addable later without changing tools or services.

---

## 3. Response Envelope

Every tool returns a consistent JSON envelope:

### Success

```json
{
  "ok": true,
  "summary": "Preflight check complete: 14/16 links OK, 2 errors found.",
  "result": { ... },
  "meta": {
    "tool_version": "1.0",
    "topology_path": "topologies/lab.json",
    "generated_at": "2026-04-10T12:34:56Z"
  }
}
```

### Failure

```json
{
  "ok": false,
  "summary": "Refused: interface ix0 is already assigned to WAN.",
  "error": {
    "code": "INTERFACE_ALREADY_ASSIGNED",
    "message": "ix0 is already bound to WAN on device opnsense"
  },
  "meta": {
    "tool_version": "1.0",
    "topology_path": "topologies/lab.json",
    "generated_at": "2026-04-10T12:34:56Z"
  }
}
```

### Output size control

Claude Code warns at 10,000 tokens and caps at 25,000 tokens for MCP tool output. Tools that can produce large results (preflight, devices) include a `detail` parameter:

- `summary` — aggregate counts and verdict only
- `standard` (default) — counts + top findings + first N detailed items
- `full` — everything (use with caution)

Large-output tools include `truncated: bool` and `total_count: int` in their result.

---

## 4. Tool Contracts (9 tools)

### Workflow tools (4)

#### `stitch_preflight_run`

Run full preflight verification: collect observations from live adapters, merge, compare against declared topology.

```
Input:
  topology_path?: string    (default: env STITCH_TOPOLOGY or "topologies/lab.json")
  scope?: string            (filter to specific devices/site)
  adapters?: [string]       (default: auto-detect from topology mcp_source fields)
  detail?: "summary" | "standard" | "full"   (default: "standard")

Output.result:
  verdict: string           ("pass" | "fail" | "error")
  total_links: int
  ok: int
  warning: int
  error: int
  findings: [               (top N findings for standard, all for full)
    { link, status, severity, checks: [{ check, port, flag, message }] }
  ]
  truncated: bool
  detail_available: bool

Output.summary:
  "Preflight: 14/16 links OK, 2 errors. ix0 missing on opnsense, onti-fe unreachable."
```

#### `stitch_trace_vlan`

Trace VLAN path through declared topology.

```
Input:
  vlan: int                 (required)
  source?: string           (device ID)
  target?: string           (device ID)

Output.result:
  vlan: int
  status: string            ("ok" | "broken")
  hops: [{ device, port, link, status, reason }]
  first_break?: { device, port, reason, likely_causes }

Output.summary:
  "VLAN 42: path from sw-core-01 to fw-main is OK (3 hops)."
```

#### `stitch_impact_preview`

Preview impact of a proposed change on the topology.

```
Input:
  action: string            ("remove_link" | "remove_vlan" | "remove_port")
  device: string            (device ID)
  port?: string
  parameters?: object

Output.result:
  proposed_change: object
  impact: [{ device, port, effect, severity }]
  risk: string              ("low" | "medium" | "high")
  safe_to_apply: bool
  highest_severity: string
  highlights: [string]

Output.summary:
  "Removing ix0 on opnsense: HIGH risk. 3 devices lose VLAN 42 connectivity."
```

#### `stitch_interface_assign` (write-path)

Assign a physical OPNsense interface to a logical role.

```
Input:
  device_id: string         (must match exactly one device)
  physical_interface: string (e.g., "ix0")
  assign_as: string         ("wan" | "lan" | "opt1" | "opt2" | ... OPNsense role names)
  description?: string
  dry_run: bool             (default: true)

Output.result:
  dry_run: bool
  before: object            (interface state before change)
  after: object             (interface state after change, or projected state if dry_run)
  verification: object      (before/after diff)
  applied: bool

Output.summary:
  "Dry run: would assign ix0 as OPT1 (FRONTEND) on opnsense. No changes applied."
  or
  "Applied: ix0 assigned as OPT1 (FRONTEND) on opnsense. Verified: interface now UP."
```

**Safety rules:**
- `dry_run` defaults to `true` — Claude Code must explicitly pass `dry_run: false` to apply
- Refuse if device_id matches zero or multiple devices
- Refuse if physical_interface is already assigned (no overwrite in v1)
- Refuse if physical_interface doesn't exist on the device
- Read state before and after every real apply
- Log every write-path call: timestamp, tool, input, before, after, success/failure

**Error codes:**
- `DEVICE_NOT_FOUND` — device_id doesn't match any device
- `DEVICE_AMBIGUOUS` — device_id matches multiple devices
- `INTERFACE_NOT_FOUND` — physical_interface doesn't exist
- `INTERFACE_ALREADY_ASSIGNED` — interface is already bound to a role
- `APPLY_FAILED` — OPNsense API returned an error during assignment
- `VERIFICATION_FAILED` — post-change state doesn't match expected state

### Read tools (5)

#### `stitch_topology_summary`

```
Input:  topology_path?: string
Output.result: { name, version, device_count, link_count, vlan_count, updated, updated_by }
Output.summary: "Lab topology: 8 devices, 16 links, 5 VLANs. Last updated 2026-04-10."
```

#### `stitch_devices`

```
Input:  topology_path?: string
Output.result: [{ id, name, type, model, management_ip, port_count, mcp_source }]
Output.summary: "8 devices: 1 firewall, 4 switches, 3 hypervisors."
```

#### `stitch_device_detail`

```
Input:  device_id: string
Output.result: { device: Device, ports: [Port] }
Output.summary: "sw-core-01 (SWITCH, USW-Pro-48): 12 ports, management IP 192.168.254.2."
```

#### `stitch_device_neighbors`

```
Input:  device_id: string
Output.result: [{ device, local_port, remote_port, link_id, link_type }]
Output.summary: "sw-core-01 has 3 neighbors: fw-main (sfp-0), sw-edge-01 (sfp-1), proxmox-01 (eth0)."
```

#### `stitch_topology_diagnostics`

```
Input:  topology_path?: string
Output.result: { dangling_ports, orphan_devices, missing_endpoints, total_devices, total_ports, total_links }
Output.summary: "Topology health: 2 dangling ports, 0 orphan devices, 1 missing endpoint."
```

---

## 5. Package Structure

```
src/stitch/mcp/
    __init__.py
    server.py               — FastMCP app, tool registration, main() entry point
    engine.py               — StitchEngine: lazy topology, gateway client, factories
    schemas.py              — Response envelope, error codes, shared types

    tools/                  — Thin: input parsing, tool decorator, envelope formatting
        __init__.py
        preflight.py        — stitch_preflight_run
        trace.py            — stitch_trace_vlan, stitch_impact_preview
        topology.py         — stitch_topology_summary, stitch_devices,
                              stitch_device_detail, stitch_device_neighbors,
                              stitch_topology_diagnostics
        interface.py        — stitch_interface_assign

    services/               — Use-case orchestration (domain logic composition)
        __init__.py
        preflight_service.py    — collect, merge, verify pipeline
        topology_service.py     — load, browse, diagnose
        interface_service.py    — read, validate, apply, verify, audit

    gateway/                — Adapter access via MCP gateway
        __init__.py
        client.py           — McpGatewayClient (reuse from contractkit or copy)
```

**Separation rule:** Tools are thin wrappers. Services contain orchestration. Engine provides shared context. Gateway handles external MCP calls. Business logic stays in the existing domain packages (verifykit, tracekit, graphkit, etc.).

---

## 6. Engine: Lazy Topology with Cache

```python
class StitchEngine:
    def __init__(self, topology_path: str, gateway_url: str) -> None:
        self.topology_path = topology_path
        self.gateway = McpGatewayClient(gateway_url)
        self._cached_topology: TopologySnapshot | None = None
        self._cached_mtime: float | None = None

    def get_topology(self, override_path: str | None = None) -> TopologySnapshot:
        path = Path(override_path or self.topology_path)
        mtime = path.stat().st_mtime
        if self._cached_topology is None or mtime != self._cached_mtime or override_path:
            self._cached_topology = load_topology(path)
            self._cached_mtime = mtime
        return self._cached_topology

    def get_explorer(self, topology: TopologySnapshot | None = None) -> ExplorerWorkflow:
        topo = topology or self.get_topology()
        return ExplorerWorkflow(topo)
```

No mutable observed state across tool calls. Every call starts from the declared topology file and live adapter queries.

---

## 7. Registration

### `.mcp.json` at repo root

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

### pyproject.toml entry

```toml
[project.scripts]
stitch-mcp = "stitch.mcp.server:main"

[project.dependencies]
# add:
fastmcp = ">=2.0.0"
```

---

## 8. Write-Path Audit Log

Every `stitch_interface_assign` call (dry_run or real) is logged to `~/.stitch/audit.jsonl`:

```json
{
  "timestamp": "2026-04-10T12:34:56Z",
  "tool": "stitch_interface_assign",
  "input": { "device_id": "opnsense", "physical_interface": "ix0", "assign_as": "opt1", "dry_run": false },
  "before": { ... },
  "after": { ... },
  "applied": true,
  "success": true,
  "error": null
}
```

One line per call, append-only.

---

## 9. Not in v1

- HTTP/SSE transport (add later with server-side auth when sharing beyond Claude Code)
- VLAN apply, config push, bridge membership changes (Phase B write-path expansion)
- Report persistence / report_id (reports are returned inline for now)
- Internal pipeline tools (collect, merge, verify separately)
- Multi-device write operations (v1 is single-device, single-interface)
- Rate limiting (single-user stdio, not needed yet)

---

## 10. Dependencies

```
stitch.mcp → stitch.core (types only)
stitch.mcp → stitch.modelkit (domain models)
stitch.mcp → stitch.contractkit (gateway client)
stitch.mcp → stitch.storekit (topology loading)
stitch.mcp → stitch.apps.explorer (ExplorerWorkflow)
stitch.mcp → stitch.apps.preflight (PreflightWorkflow)
stitch.mcp → stitch.verifykit, tracekit, graphkit (pure domain logic)
stitch.mcp → fastmcp (MCP protocol)
```

No client packages (CLI, TUI, lite, web) depend on stitch.mcp. No stitch.mcp depends on client packages.
