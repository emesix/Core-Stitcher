# VOS-Ruggensgraat — Explorer v0 Briefing

**Date:** 2026-04-08 (updated same day)
**Status:** Topology domain pack complete — 475 tests, all lane items shipped

---

## What is this project?

VOS-Ruggensgraat is a modular agentic backend for home lab network infrastructure management. It merges three things into one monorepo:

1. **VOS-Workbench** — a headless runtime spine (module system, event bus, config trees, persistence, FastAPI API layer, topological startup ordering). Think of it as a stripped-down application server purpose-built for composing domain modules.

2. **Preflight** — a network topology verification engine. It collects live state from managed switches (via MCP/telnet), firewalls (OPNsense MCP), and hypervisors (Proxmox MCP), merges those observations into a canonical snapshot, and compares it against a declared topology to find mismatches, trace VLAN paths, and preview the impact of changes.

3. **Explorer** — a read-only topology browser. Same data model, same backbone, no collection/verification — just navigation and query.

The key architectural idea: **Preflight is the verifier. Explorer is the navigator. Same backbone underneath.**

---

## Architecture in brief

```
contractkit        — interaction protocols (verbs), no logic
modelkit           — domain data types (nouns): Device, Port, Link, VLAN, TopologySnapshot, etc.
graphkit           — pure graph traversal library (neighbors, BFS, VLAN filtering, diagnostics)
storekit           — topology JSON serialization

switchcraft        — switch adapter (MCP/telnet → Observations)
opnsensecraft      — OPNsense adapter (MCP/REST → Observations) [stub]
proxmoxcraft       — Proxmox adapter (MCP/API → Observations) [stub]
collectkit         — merge observations into a canonical snapshot
verifykit          — compare declared vs observed topology
tracekit           — VLAN path tracing + change impact preview
interfacekit       — HTTP routes for both Preflight and Explorer

apps/preflight     — workflow: collect → merge → verify → trace → expose
apps/explorer      — workflow: load → query via graphkit/tracekit → expose
```

Hard dependency rules (enforced):
- contractkit → nothing
- Pure libraries (modelkit, graphkit, storekit) → contractkit only
- Runtime modules → pure libraries + contractkit + spine SDK
- Apps → public module interfaces via contractkit protocols + spine bootstrap
- Adapters never import each other

---

## What Explorer v0 delivers

Explorer v0 is a thin read-only layer over the Preflight backbone. It answers:

| Question | Endpoint | Backed by |
|----------|----------|-----------|
| What's the full topology? | `GET /explorer/topology` | storekit |
| What devices exist? | `GET /explorer/devices` | modelkit |
| What are a device's ports, config, type? | `GET /explorer/devices/{id}` | modelkit |
| What's connected to this device? | `GET /explorer/devices/{id}/neighbors` | graphkit.neighbors() |
| Which ports carry VLAN 25? | `GET /explorer/vlans/25` | graphkit.vlan_ports() |
| What's broken, dangling, or undefined? | `GET /explorer/diagnostics` | graphkit.diagnostics() |
| Where does VLAN 25 go from switch sw1? | `POST /explorer/trace` | tracekit |
| What breaks if I remove this link/port/VLAN? | `POST /explorer/impact` | tracekit |

All queries run on the **declared topology** (a hand-maintained JSON file that is the source of truth for V1). No MCP calls, no collection, no verification — just navigation.

---

## graphkit — the shared traversal layer

graphkit is the new pure library that makes Explorer possible. It was designed to be reusable by both Preflight and Explorer (and any future app).

| Function | What it does |
|----------|-------------|
| `neighbors(snapshot, device_id)` | All adjacent devices via links, with port and link metadata |
| `bfs(snapshot, start, predicate?)` | Breadth-first traversal with optional filter |
| `vlan_ports(snapshot, vlan_id)` | All ports carrying a specific VLAN, sorted by device/port |
| `dangling_ports(snapshot)` | Ports with no links attached |
| `orphan_devices(snapshot)` | Devices that appear in no link |
| `missing_endpoints(snapshot)` | Links referencing non-existent devices or ports |
| `diagnostics(snapshot)` | Composite of the above + totals |
| `subgraph(snapshot, device_ids)` | Extract a subset of the topology |

All functions are pure (no I/O, no state, no spine dependency). Input is always an explicit `TopologySnapshot`. They can be unit-tested in complete isolation.

---

## How Explorer differs from Preflight

| | Preflight | Explorer |
|---|---|---|
| **Purpose** | Verify live state matches declared truth | Browse and query declared topology |
| **Data pipeline** | collect → merge → verify | load → query |
| **Protocol** | `PreflightWorkflowProtocol` (async) | `ExplorerWorkflowProtocol` (sync) |
| **Why async/sync** | Calls MCP adapters (network I/O) | Reads JSON file + runs pure functions |
| **Core verbs** | verify, trace, impact | neighbors, vlan map, diagnostics, trace, impact |
| **Source of truth** | Declared vs observed comparison | Declared only |

They share: modelkit types, storekit loader, tracekit engines, and now graphkit.

---

## Current state — what works

- **475 passing tests** (was 394 before Explorer, 456 after Explorer v0 endpoints)
- **Preflight:** Full pipeline working — switchcraft collects from real switches via MCP gateway, collectkit merges, verifykit compares, tracekit traces VLANs and previews impact. All exposed over HTTP.
- **Explorer:** All 8 query endpoints + visual layer. Topology cached at init with explicit `reload()`. Wired into the spine as a soft dependency — routes mount automatically when ExplorerWorkflow is registered.
- **Impact engine:** Supports three actions — `remove_link`, `remove_vlan`, `remove_port`.
- **Three adapters:** switchcraft, opnsensecraft, proxmoxcraft — all real, all with MCP gateway integration, normalizers, and fixture-backed tests.
- **History/diff:** Pure `diff_reports()` engine compares two VerificationReports. Exposed at `POST /diff`. Deterministic output with added/removed/changed/unchanged summaries at both link and check level.
- **Visual layer:** Single-page HTML at `GET /explorer/ui`. SVG topology graph with draggable nodes, device inspector panel, diagnostics bar. No build step, no framework.
- **Lint/format/tests all green.**

---

## What was shipped (hardening lane, all complete)

1. ~~**Cache topology in ExplorerWorkflow**~~ — loaded once at init, `reload()` for explicit refresh.
2. ~~**Wire Explorer into the spine**~~ — soft dependency via `resolve_all(ExplorerWorkflowProtocol)`. Health reports explorer status.
3. ~~**Real opnsensecraft + proxmoxcraft**~~ — full MCP gateway integration, normalizers, fixture-backed tests.
4. ~~**History/diff**~~ — pure diff engine + `POST /diff` endpoint.
5. ~~**Explorer visual layer**~~ — `GET /explorer/ui`, SVG graph, device inspector, diagnostics bar.

## What comes next

### Consolidation (optional polish)

- **graphkit for tracekit** — tracekit has its own ad-hoc BFS. It could delegate to graphkit's `bfs()` for consistency. Not urgent, but would reduce duplication.
- **Diff persistence** — current diff is stateless (pass two reports in). A storage layer for verification runs would enable historical comparison.

### Second domain

- **Searchcraft integration** — the architecture was designed to support multiple domains on the same spine. Searchcraft (deep research agent) would become `vos.apps.researcher` with its own providers → collectkit → synthesiskit pipeline. The patterns are proven.

---

## The core architectural bet

The project bets that **one shared backbone** (modelkit types + graphkit traversal + storekit serialization + spine runtime) can serve multiple domain applications without fragmentation.

Explorer v0 was built in a single session by composing existing pure libraries. The hardening lane (cache, spine wiring, diff, visual layer) was completed in a follow-up session with no architecture drift. The full topology domain pack — from MCP adapter to visual browser — shipped in 475 tests with zero dependency violations.

This is the pattern for Searchcraft and any future domain: define adapter modules, compose through pure libraries, expose through interfacekit, orchestrate through a thin app shell.
