# VOS-Ruggensgraat — Architecture Design Specification

**Date:** 2026-04-07
**Status:** Frozen — ready for implementation planning
**Repository:** VOS-Ruggensgraat

---

## 1. One-Sentence Summary

VOS-Ruggensgraat merges the VOS-Workbench runtime spine with the Preflight/NetMap domain designs into a single monorepo of reusable modules — pure domain libraries, spine-registered runtime modules, and thin app shells — connected through explicit contracts and a narrow spine SDK.

---

## 2. Origin

Three projects converge:

- **VOS-Workbench** — a modular headless agentic backend, built from scratch inspired by Claude Code's internal architecture. Provides: module system (UUID-based instances), async event bus, config tree (YAML + Pydantic), SQLModel persistence, Alembic migrations, FastAPI API layer, topological startup ordering, entry point discovery. Python 3.14, alpha phase, 20+ passing tests.

- **VOS-Preflight / VOS-NetMap design specs** — design documents from VOS-Network-Redux defining a port-and-link truth model with live verification, VLAN tracing, change impact preview, and topology visualization. Defines the domain language: Device, Port, Link, VLAN, Observation, Mismatch. No code — specs only.

- **Merger concept** — a design conversation establishing that these projects share a common domain backbone and should be structured as: shared reusable modules (pure libraries + runtime modules) consumed by thin app shells (preflight, explorer). Adapters (switchcraft, opnsensecraft, proxmoxcraft) become first-class modules rather than parallel mini-systems.

**Homelable** provided inspiration for the Preflight/NetMap concept (health checks, MCP patterns, device discovery) but contributes no code.

---

## 3. Architecture: Approach C

**Monorepo with namespace packages and Workbench module registration.**

One repository, one `pyproject.toml`. Domain modules live under `vos.*` namespace. Pure libraries stay independent of the spine. Runtime modules register via `vos.modules` entry points and are discovered at startup.

### 3.1 Migration Strategy

`vos_workbench` is NOT renamed on day 1. The existing package stays intact with its import paths, tests, and Alembic migrations. New domain modules are added alongside under `vos.*`. The rename to `vos.spine` happens in a dedicated phase after new module boundaries are proven.

### 3.2 Package Structure

```
VOS-Ruggensgraat/
├── src/
│   ├── vos_workbench/               # UNCHANGED — runtime spine
│   │   ├── __init__.py
│   │   ├── api/                     # FastAPI app factory, routes
│   │   ├── config/                  # Config models, YAML loader
│   │   ├── events/                  # Event bus, VosEvent model
│   │   ├── registry/                # ModuleTypeRegistry, entry point discovery
│   │   ├── runtime/                 # Runtime orchestrator, startup planner
│   │   ├── sdk/                     # NEW — public module-facing SDK (see Section 5)
│   │   ├── storage/                 # DB engine, Alembic, repositories, persistence
│   │   ├── uri/                     # VosReference parser
│   │   └── errors.py
│   └── vos/                         # implicit namespace package (NO __init__.py)
│       ├── contractkit/             # module interaction protocols, capability manifests
│       ├── modelkit/                # Device, Port, Link, VLAN, TopologySnapshot, etc.
│       ├── graphkit/                # traversal, filtering, neighbors, subgraph
│       ├── storekit/                # snapshot serialization, schema versioning, diff
│       ├── switchcraft/             # switch adapter (spine module)
│       ├── opnsensecraft/           # OPNsense adapter (spine module)
│       ├── proxmoxcraft/            # Proxmox adapter (spine module)
│       ├── collectkit/              # normalize + merge observations into snapshot
│       ├── verifykit/               # verification engine
│       ├── tracekit/                # trace / impact / break analysis
│       ├── interfacekit/            # API routes, MCP exposure, DTO mapping
│       └── apps/
│           ├── preflight/           # thin workflow composition shell
│           └── explorer/            # later
├── tests/
│   ├── vos_workbench/               # existing spine tests (untouched)
│   ├── contractkit/
│   ├── modelkit/
│   ├── graphkit/
│   ├── storekit/
│   ├── switchcraft/
│   ├── opnsensecraft/
│   ├── proxmoxcraft/
│   ├── collectkit/
│   ├── verifykit/
│   ├── tracekit/
│   ├── interfacekit/
│   └── apps/
│       └── preflight/
├── docs/
│   ├── architecture/                # from Workbench (core-thesis, spine-definition, etc.)
│   └── specs/                       # merged design specs
├── alembic/                         # database migrations (from Workbench)
├── schemas/                         # JSON schemas (from Workbench)
├── pyproject.toml                   # single package
├── CLAUDE.md
└── README.md
```

---

## 4. Module Classification

### 4.1 Layers

| Layer | Packages | Rule |
|-------|----------|------|
| **Contracts** | `contractkit` | Defines interaction protocols and capability manifests. No logic, no I/O, no domain objects. |
| **Pure libraries** | `modelkit`, `graphkit`, `storekit` | May depend on `contractkit`. No spine dependency, no network calls. `storekit` does local file I/O for topology snapshots by design — but no DB access, no MCP calls, no spine storage. |
| **Runtime modules** | `switchcraft`, `opnsensecraft`, `proxmoxcraft`, `collectkit`, `verifykit`, `tracekit`, `interfacekit` | May depend on pure libraries, `contractkit`, and `vos_workbench.sdk.*`. Register via entry points. |
| **Spine** | `vos_workbench` | Runtime, config, events, storage, registry. Discovers and manages modules. |
| **Apps** | `vos.apps.preflight`, `vos.apps.explorer` | Compose modules via public interfaces. Bootstrap spine. Almost zero domain logic. |

### 4.2 Dependency Rule (hard, enforced)

**Allowed:**

```
apps  →  public module interfaces (via contractkit protocols) + spine bootstrap
modules  →  pure libraries + contractkit + vos_workbench.sdk.*
pure libraries  →  contractkit
contractkit  →  nothing (intentionally part of the core dependency base — must stay protocol-only)
```

**Not allowed:**

- Adapter → adapter imports (switchcraft must not import opnsensecraft)
- verifykit calling switchcraft directly (gets data from caller)
- tracekit reading DB tables (gets snapshot from caller)
- interfacekit importing module internals (resolves workflow facade only)
- Any module importing from `vos_workbench.runtime`, `vos_workbench.storage`, `vos_workbench.events.bus`, or other spine internals
- Apps importing deep internals from modules (only public interfaces)

### 4.3 Ownership Split

**`modelkit`** owns domain data types — the nouns:

| Type | Description |
|------|-------------|
| `Device` | Physical or virtual thing with ports |
| `Port` | Interface on a device (sfp+, ethernet, bridge, vlan, virtual) |
| `Link` | Connection between two ports (physical_cable, bridge_member, vlan_parent, internal_virtual) |
| `VlanMembership` | VLAN config on a port (mode, native, tagged) |
| `VlanMetadata` | VLAN registry entry (name, color, subnet, gateway) |
| `TopologySnapshot` | Complete topology container (devices, ports, links, VLANs) |
| `Observation` | Live state observation from an adapter |
| `Mismatch` | Declared-vs-observed divergence |
| `MergeConflict` | Ambiguity from merging multiple adapter observations |
| `VerificationReport` | Full verification result (per-link checks, summary) |
| `TraceRequest` | VLAN trace input (vlan, source, target) |
| `TraceResult` | Ordered hop trace with break point |
| `ImpactRequest` | Change preview input (action, device, port, parameters) |
| `ImpactResult` | Affected set with risk assessment |

**`contractkit`** owns module interaction protocols — the verbs:

| Type | Description |
|------|-------------|
| `CollectorProtocol` | Service interface for adapter modules (collect → observations) |
| `MergerProtocol` | Service interface for collectkit (merge → snapshot + conflicts) |
| `VerifierProtocol` | Service interface for verifykit (verify → report) |
| `TracerProtocol` | Service interface for tracekit (trace → result, preview → impact) |
| `PreflightWorkflowProtocol` | Workflow facade for the full preflight sequence |
| `CapabilityManifest` | What a module type declares it can do |
| `ModuleHealth` | Standard health status shape |
| `ModuleStatus` | Standard operational status shape |

---

## 5. Spine SDK

The only `vos_workbench` imports allowed by runtime modules.

### 5.1 SDK Package

```
vos_workbench/sdk/
  __init__.py              # re-exports public surface
  module_type.py           # Protocol/base for module types
  manifest.py              # CapabilityManifest, config schema declaration
  events.py                # EventPublisher, EventSubscription protocols
  config.py                # ConfigAccessor protocol
  context.py               # ModuleContext (injected at startup)
  capabilities.py          # CapabilityResolver protocol
```

### 5.2 SDK Surface

| Component | Purpose |
|-----------|---------|
| `ModuleType` protocol | Base with `type_name`, `version`, `config_model`, lifecycle hooks (`start`, `stop`, `health`) |
| `ModuleManifest` | Capability declarations, required capabilities, config schema reference. Belongs to the TYPE. |
| `ModuleContext` | Injected at startup. Bundles publisher, config, logger, capability resolver. The module's only handle to the spine. |
| `EventPublisher` protocol | `publish(event)` — emit events for audit/telemetry |
| `EventSubscription` protocol | `subscribe(type_pattern, source_glob)` — filtered event stream |
| `ConfigAccessor` protocol | Returns already-validated typed config model. Module never sees raw dicts. |
| `CapabilityResolver` protocol | Cardinality-aware module resolution (see 5.3) |

### 5.3 Capability Resolution (cardinality-aware)

```python
class CapabilityResolver(Protocol):
    def resolve_one[T](self, protocol: type[T], *, selector: str | None = None) -> T:
        """Single instance. Raises AmbiguousCapability if multiple match without selector."""

    def resolve_all[T](self, protocol: type[T]) -> list[T]:
        """All instances implementing this protocol."""

    def resolve_named[T](self, protocol: type[T], instance_id: str | UUID) -> T:
        """Specific instance by UUID or module name."""
```

Use cases:
- `resolve_all(CollectorProtocol)` — get all adapters for fan-out collection
- `resolve_one(MergerProtocol)` — single collectkit instance
- `resolve_named(CollectorProtocol, "switchcraft-onti-be")` — specific switch adapter

### 5.4 Type vs Instance vs Manifest

| Concept | What | Where | Cardinality |
|---------|------|-------|-------------|
| **ModuleType** | Class-level metadata: `type_name`, `version`, `config_model` | Defined by module package, registered via entry points | One per module kind |
| **ModuleManifest** | Capability declarations, required capabilities, config schema ref | Class attribute on ModuleType | One per ModuleType |
| **ModuleInstance** | Runtime object: UUID, validated config, lifecycle state, health | Created by spine from YAML config + ModuleType | Many per ModuleType |

One ModuleType can have multiple instances. Two switchcraft instances for two switches. Three proxmoxcraft instances for three cluster nodes.

### 5.5 Typed Config Injection

1. ModuleType declares `config_model = SwitchcraftConfig` (Pydantic model)
2. Spine reads raw YAML, validates against `config_model`, fails at startup if invalid
3. Module instance receives validated typed object via `ModuleContext.config`
4. Module code uses typed fields: `self.context.config.host` — no raw dict parsing

---

## 6. Interaction Model

### 6.1 Hard Rule

**Service-primary for workflow execution. Events for audit/telemetry only.**

Events never carry hidden control flow. The workflow is a deterministic chain of capability calls.

### 6.2 Module Interaction Table

| Module | Primary interaction | Events emitted |
|--------|-------------------|----------------|
| **switchcraft** | `collect() → list[Observation]` | `collection.started`, `collection.completed`, `collection.error` |
| **opnsensecraft** | `collect() → list[Observation]` | same pattern |
| **proxmoxcraft** | `collect() → list[Observation]` | same pattern |
| **collectkit** | `merge(observations) → (TopologySnapshot, list[MergeConflict])` | `merge.completed`, `merge.conflict` |
| **verifykit** | `verify(declared, observed) → VerificationReport` | `verification.completed`, `verification.mismatch_found` |
| **tracekit** | `trace(snapshot, request) → TraceResult` | `trace.completed`, `trace.break_found` |
| **tracekit** | `preview(snapshot, request) → ImpactResult` | `impact.completed` |
| **interfacekit** | Resolves `PreflightWorkflowProtocol`, maps to HTTP/MCP | `request.received`, `request.completed` |
| **preflight** | Implements `PreflightWorkflowProtocol`, orchestrates full sequence | `workflow.started`, `workflow.completed` |

### 6.3 Data Flow

```
switchcraft ─┐
opnsensecraft┼─→ list[Observation] ──→ collectkit.merge()
proxmoxcraft ┘                              │
                                            ├──→ TopologySnapshot (observed)
                                            └──→ list[MergeConflict]
                                                    │
storekit.load() ──→ TopologySnapshot (declared)     │
                          │                         │
                          ├─────────────────────────┘
                          ▼
                    verifykit.verify(declared, observed)
                          │
                          ▼
                    VerificationReport
                          │
                          ▼
                    tracekit.trace(snapshot, request)
                          │
                          ▼
                    TraceResult / ImpactResult
                          │
                          ▼
                    interfacekit (HTTP/MCP)
```

### 6.4 Explicit-Input Rules

- **verifykit** is a pure evaluator: two snapshots in, report out. Never loads files, never queries DB, never calls adapters.
- **tracekit** receives `TopologySnapshot` as explicit input. Never loads its own state.
- **collectkit** builds "what we think the world looks like." Does not verify correctness, decide policy, or analyze impact.
- The **caller** (preflight workflow) is responsible for obtaining inputs and routing outputs.

### 6.5 interfacekit → Workflow Facade

interfacekit does NOT resolve low-level modules. It resolves the workflow facade:

```
interfacekit  →  PreflightWorkflowProtocol  →  preflight orchestrates
                                                    ├── resolve_all(CollectorProtocol)
                                                    ├── MergerProtocol
                                                    ├── VerifierProtocol
                                                    └── TracerProtocol
```

interfacekit's sub-boundaries (internal discipline):
- **Transport adapters**: HTTP routes, MCP tool definitions
- **DTO/response mapping**: domain types → API response shapes
- **Workflow service layer**: resolves workflow facade, translates requests

---

## 7. Module Responsibility Table

| Package | Layer | Responsibility | Inputs | Outputs | Dependencies |
|---------|-------|---------------|--------|---------|-------------|
| **contractkit** | Contracts | Module interaction protocols, capability manifests, health shapes | — | Protocol types, manifest types | None |
| **modelkit** | Pure library | Canonical domain objects with validation and identity rules | — | All domain data types (see 4.3) | `contractkit` |
| **graphkit** | Pure library | Graph traversal on topology: neighbors, BFS/DFS, subgraph, VLAN filtering | `TopologySnapshot` | Paths, subgraphs, neighbor sets | `contractkit`, `modelkit` |
| **storekit** | Pure library | Topology snapshot serialization, schema versioning, diff, import/export | File path or bytes | `TopologySnapshot`, diffs, migration results | `contractkit`, `modelkit` |
| **switchcraft** | Runtime module | Collect live state from managed switches (telnet/HTTP), normalize to observations | Switch connection config | `list[Observation]` | `contractkit`, `modelkit`, spine SDK |
| **opnsensecraft** | Runtime module | Collect live state from OPNsense (MCP/API), normalize to observations | OPNsense connection config | `list[Observation]` | `contractkit`, `modelkit`, spine SDK |
| **proxmoxcraft** | Runtime module | Collect live state from Proxmox (MCP/API), normalize to observations | Proxmox connection config | `list[Observation]` | `contractkit`, `modelkit`, spine SDK |
| **collectkit** | Runtime module | Accept observations from adapters, normalize, merge into canonical snapshot, emit conflicts | `list[Observation]` | `(TopologySnapshot, list[MergeConflict])` | `contractkit`, `modelkit`, spine SDK |
| **verifykit** | Runtime module | Compare declared vs observed state: link checks, MAC checks, VLAN compatibility | Two `TopologySnapshot`s (declared + observed) | `VerificationReport` | `contractkit`, `modelkit`, spine SDK |
| **tracekit** | Runtime module | VLAN trace, break detection, impact preview on explicit snapshot input | `TopologySnapshot` + request | `TraceResult`, `ImpactResult` | `contractkit`, `modelkit`, `graphkit`, spine SDK |
| **interfacekit** | Runtime module | Expose workflow capabilities via HTTP routes and MCP tools. DTO mapping. | `PreflightWorkflowProtocol` via resolver | HTTP responses, MCP tool results | `contractkit`, `modelkit`, spine SDK |
| **preflight** | App shell | Implement `PreflightWorkflowProtocol`. Orchestrate: collect → merge → verify → trace → expose | User/AI trigger | Workflow results | Public module interfaces via contractkit, spine bootstrap |

---

## 8. Domain Model (from Preflight Final Design, rev3)

### 8.1 Core Entities

Three stored entities. VLANs are properties of ports, not separate operational objects.

| Entity | What it represents |
|--------|-------------------|
| **Device** | A physical or virtual thing that has ports |
| **Port** | An interface on a device — physical, bridge, VLAN subinterface, or virtual NIC |
| **Link** | A connection between two ports — physical cable OR internal logical hop |

Ports are the **vertices**. Links are the **edges**. The graph engine treats all link types identically for traversal. Verification checks differ by link type.

### 8.2 Port Types

| Type | Examples | Notes |
|------|----------|-------|
| `sfp+` | Switch SFP+ ports | Physical, may need SFP module |
| `ethernet` | RJ45 NICs | Physical copper |
| `bridge` | vmbr0, bridge0 | Logical. Members listed via bridge_member links |
| `vlan` | vlan01, vlan02 | Logical. Parent via vlan_parent link |
| `virtual` | vtnet0 | VM/hypervisor internal NIC |

### 8.3 Link Types

| Type | Represents | Verification checks |
|------|-----------|-------------------|
| `physical_cable` | External cable | Link up/down, neighbor MAC, VLAN compatibility |
| `bridge_member` | Port is member of bridge | Membership exists, bridge_vlan_aware, bridge_vids |
| `vlan_parent` | VLAN subinterface on trunk | Parent up, VLAN ID on parent |
| `internal_virtual` | VM NIC to bridge, backplane | Interface present and up |

### 8.4 Observation Confidence

| Source | Meaning | Trust level |
|--------|---------|-------------|
| `mcp_live` | Queried from MCP tool just now | Highest |
| `declared` | From topology file | High (human-reviewed) |
| `inferred` | Derived from other observations | Medium |
| `unknown` | No data available | Lowest |

Verifier trusts `mcp_live` over `declared` when they conflict.

### 8.5 VLAN Compatibility Rules

| Port A | Port B | Compatible? |
|--------|--------|-------------|
| Trunk tagged [25,254] | Trunk tagged [254] | Yes — subset subscription |
| Trunk tagged [25,254] | Access VLAN 254 | Yes — switch terminates trunk |
| Access VLAN 25 | Access VLAN 254 | No — different VLANs |
| Trunk tagged [25] | Trunk tagged [254] | Flag — no shared VLANs |

### 8.6 Identity Rules

- Devices keyed by slug (e.g., `onti-be`, `pve-hx310-db`)
- Ports keyed by alias within device (e.g., `eth1`, `vmbr0`)
- Links keyed by explicit ID (e.g., `phys-opnsense-ix1-to-onti-be-eth1`)
- MAC addresses are evidence/verification truth, not primary identity
- Ports have both `device_name` (native vendor name) and key (alias)

### 8.7 Model Authority

`topology.json` is the reviewed working truth for V1. Not the forever-architecture. It may later be ingested from NetBox or generated from live discovery. For now it is hand-maintained and git-tracked.

---

## 9. MCP Adapters

Each device type maps to an MCP source for live queries:

| Device type | MCP tool | What we query |
|-------------|----------|--------------|
| Switch (onti-ogf) | switchcraft + telnet | Port status, VLAN membership, MAC table |
| Switch (jtcom) | switchcraft + HTTP | Port status, VLAN membership, MAC table |
| Firewall (OPNsense) | opnsense MCP | Interface status, IPs, VLAN config |
| Hypervisor (Proxmox) | proxmox MCP | Bridge config, bridge_vids, NIC status |

All adapters normalize their output to `list[Observation]` using the modelkit types. Vendor-specific quirks stay inside the adapter. Never leak into shared modules.

---

## 10. Entry Point Registration

Runtime modules register via `pyproject.toml` entry points under the `vos.modules` group:

```toml
[project.entry-points."vos.modules"]
"resource.switchcraft" = "vos.switchcraft:SwitchcraftModule"
"resource.opnsensecraft" = "vos.opnsensecraft:OpnsensecraftModule"
"resource.proxmoxcraft" = "vos.proxmoxcraft:ProxmoxcraftModule"
"resource.collectkit" = "vos.collectkit:CollectkitModule"
"core.verifykit" = "vos.verifykit:VerifykitModule"
"core.tracekit" = "vos.tracekit:TracekitModule"
"integration.interfacekit" = "vos.interfacekit:InterfacekitModule"
```

The spine's `ModuleTypeRegistry.discover_entry_points()` loads these at startup.

---

## 11. What Moves Where

### From VOS-Workbench-standalone

| Source | Destination | Notes |
|--------|-------------|-------|
| `src/vos_workbench/` | `src/vos_workbench/` | Stays intact, no rename |
| `tests/` | `tests/vos_workbench/` | Existing tests, untouched |
| `docs/architecture/` | `docs/architecture/` | Core thesis, spine definition, alpha proposals |
| `alembic/` | `alembic/` | Database migrations |
| `schemas/` | `schemas/` | JSON schemas |
| `pyproject.toml` | `pyproject.toml` | Extended with new packages |
| `CLAUDE.md` | `CLAUDE.md` | Updated for new structure |

### From VOS-Network-Redux (specs only)

| Source | Destination | Notes |
|--------|-------------|-------|
| `docs/superpowers/specs/2026-04-07-vos-preflight-final-design.md` | `docs/specs/` | Authoritative domain design |
| `docs/superpowers/specs/2026-04-07-network-topology-visualizer-design.md` | `docs/specs/` | NetMap design (reference) |
| `docs/superpowers/specs/2026-04-07-vos-preflight-counter-proposal.md` | `docs/specs/` | Counter-proposal (reference) |

### New (created during scaffolding)

| What | Location |
|------|----------|
| `vos_workbench/sdk/` | Spine SDK package |
| `vos/contractkit/` | Module interaction protocols |
| `vos/modelkit/` | Domain model stubs |
| `vos/graphkit/` | Graph traversal stubs |
| `vos/storekit/` | Snapshot serialization stubs |
| `vos/switchcraft/` | Switch adapter stub |
| `vos/opnsensecraft/` | OPNsense adapter stub |
| `vos/proxmoxcraft/` | Proxmox adapter stub |
| `vos/collectkit/` | Collector/merger stub |
| `vos/verifykit/` | Verification engine stub |
| `vos/tracekit/` | Trace/impact engine stub |
| `vos/interfacekit/` | API/MCP exposure stub |
| `vos/apps/preflight/` | App shell stub |

---

## 12. Frozen Decisions

These are locked unless forced to change:

1. One repo, one `pyproject.toml`, one test tree
2. `vos_workbench` stays intact in phase 1 — no rename
3. New domain modules under `vos.*` implicit namespace
4. `contractkit` = interaction protocols only, no domain objects, no logic
5. `modelkit` = all domain data types, the single source of truth for nouns
6. Service-primary interaction model; events for audit/telemetry only
7. `verifykit` and `tracekit` are pure evaluators with explicit inputs
8. Runtime modules import only from `vos_workbench.sdk.*`, never spine internals
9. Apps import only public module interfaces via contractkit protocols
10. `interfacekit` resolves workflow facades, never low-level modules
11. Capability resolution is cardinality-aware (resolve_one, resolve_all, resolve_named)
12. Module config is typed and validated before module code sees it
13. One ModuleType can have multiple instances (multi-device support)
14. Adapters hide vendor quirks — never leak into shared modules
15. `topology.json` is the V1 truth source, hand-maintained and git-tracked

---

## 13. What Must Be Built Before First Domain Code

1. **Spine SDK package** (`vos_workbench/sdk/`) — ModuleType protocol, ModuleContext, EventPublisher, ConfigAccessor, CapabilityResolver protocols
2. **contractkit** — CollectorProtocol, MergerProtocol, VerifierProtocol, TracerProtocol, PreflightWorkflowProtocol, CapabilityManifest
3. **modelkit** — Device, Port, Link, VlanMembership, TopologySnapshot, Observation, Mismatch, VerificationReport, TraceRequest/Result, ImpactRequest/Result, MergeConflict
4. **storekit** — topology.json loader/saver, schema version check
5. **Scaffolding** — all module subpackages with `__init__.py` (but NOT `src/vos/` itself — that stays as an implicit namespace package with no `__init__.py`), entry points in pyproject.toml
6. **CLAUDE.md** — updated with new structure, dependency rules, conventions
