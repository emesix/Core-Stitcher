# Integration Plan: Core-Stitcher — Grounded Edition

> Rewrite of ChatGPT's integration plan, validated against the actual codebase.
> Every file path exists. Every "already done" is verified. Every effort estimate is based on real code.

---

## What Already Exists (ChatGPT didn't know this)

| Capability | File | Status |
|---|---|---|
| RunStore protocol | `src/vos/agentcore/storekit/protocol.py` | Done — `RunStore(Protocol)` with save/get/list_runs/delete |
| JSON run persistence | `src/vos/agentcore/storekit/json_store.py` | Done — `JsonRunStore` |
| Run/step/review models | `src/vos/agentcore/storekit/models.py` | Done — RunRecord, StepRecord, TaskExecution |
| Full orchestration loop | `src/vos/agentcore/orchestration/runner.py` | Done — plan→execute→review→correct with budget |
| Budget policies | `src/vos/agentcore/orchestration/budget.py` | Done — tier filtering, prefer_local, max_ai_steps |
| LocalExecutor (A770) | `src/vos/agentcore/executorkit/local.py` | Done — wraps OpenAICompatExecutor, health-aware, pointed at `192.168.254.50:11434/v1` |
| OpenAI-compat executor | `src/vos/agentcore/executorkit/openai_compat.py` | Done — works with any OpenAI-style endpoint |
| TopologyExecutor | `src/vos/agentcore/executorkit/topology.py` | Done — routes topology actions to REST endpoints |
| Executor registry | `src/vos/agentcore/registry/executor_registry.py` | Done — find_for_task(), healthy_executors() |
| Preflight workflow | `src/vos/apps/preflight/workflow.py` | Done — collect→merge→verify with asyncio.gather |
| Explorer workflow | `src/vos/apps/explorer/workflow.py` | Done — read-only topology browser |
| project-stitcher CLI | `src/vos/apps/project_stitcher/cli.py` | Done — planning + formatted output |
| SwitchcraftCollector | `src/vos/switchcraft/collector.py` | Done — calls MCP gateway tools (device-status, get-ports, get-vlans) |
| OpnsensecraftCollector | `src/vos/opnsensecraft/collector.py` | Done |
| ProxmoxcraftCollector | `src/vos/proxmoxcraft/collector.py` | Done |
| Alembic + SQLModel | `alembic/`, `src/vos_workbench/storage/` | Done — DB infrastructure exists |
| Event bus | `src/vos_workbench/events/bus.py` | Done — async pub/sub |
| 67 test files | `tests/` | Done — 1.47 test:code ratio |

**Bottom line:** ~60% of ChatGPT's PRs #1–#3 describe code that's already written and tested.

---

## The Actual Lab (from VOS-Network-Redux)

### Devices

| Device | Model | IP | Role | Collector |
|---|---|---|---|---|
| OPNsense | VM on Qotom | 192.168.254.1 | Gateway/firewall | opnsensecraft |
| ONTi-FE | S508CL-8S | 192.168.254.31 | Frontend L2 switch (8x 10G SFP+) | switchcraft |
| ONTi-BE | S508CL-8S | 192.168.254.30 | Backend L2 switch (8x 10G SFP+) | switchcraft |
| 91TSM | S207CW-91TSM | 192.168.254.32 | Copper breakout (frontend) | switchcraft |
| Zyxel GS1900 | GS1900-24HP | 192.168.254.33 | PoE for WiFi APs | switchcraft |
| pve-qotom-1u | Mini PC | 192.168.254.100 | Proxmox host (16GB) | proxmoxcraft |
| pve-hx310-db | HX310 | 192.168.254.101 | Proxmox node (32GB) | proxmoxcraft |
| pve-hx310-arr | HX310 | 192.168.254.102 | Proxmox node (64GB) | proxmoxcraft |

### Active VLANs

| VLAN | Subnet | Purpose |
|---|---|---|
| untagged | 172.16.0.0/24 | Bypass (emergency, igc1) |
| 25 | 192.168.25.0/24 | General LAN (frontend) |
| 254 | 192.168.254.0/24 | Management |

### Current Blocker

**ONTi-BE ports 7/8 have no SFP modules installed.** Backend path (OPNsense ix1 → ONTi-BE → HX310 eth1 → vmbr1) is physically broken. HX310s reach management via frontend path only (91TSM → eth0 → vmbr0.254). SFP modules ordered 2026-04-07.

---

## Switchcraft Write Surface (actually available via MCP gateway)

Core-Stitcher can call these Switchcraft MCP tools TODAY via `localhost:4444`:

| Tool | What it does | Safe? |
|---|---|---|
| `switchcraft-create-vlan` | Create/modify VLAN with port assignment, supports `dry_run` | Yes with dry_run |
| `switchcraft-delete-vlan` | Remove VLAN from device | Risky |
| `switchcraft-configure-port` | Enable/disable, set speed, supports `dry_run` | Yes with dry_run |
| `switchcraft-apply-config` | Declarative desired state → auto-diff → apply + rollback | Yes with dry_run |
| `switchcraft-config-status` | Check drift: IN_SYNC / DRIFT / UNMANAGED | Read-only |
| `switchcraft-config-save` | Capture running config to git-versioned desired state | Read-only |
| `switchcraft-config-sync` | Apply desired state from git, auto-rollback on error | Yes with dry_run |
| `switchcraft-config-diff` | Git diff between config versions | Read-only |
| `switchcraft-save-config` | `write memory` equivalent | Safe |
| `switchcraft-execute-batch` | Batch read commands (3-5x faster) | Read-only |

**Key:** `apply-config` with `dry_run=true` is the safe entry point for the write path. Preview first, apply second.

---

## Revised Phase Plan

### Phase 1 — Lab Topology File + Live Smoke Test

**Goal:** Create the declared topology JSON for the real lab, run `PreflightWorkflow` against live devices.

**What needs building:**
- `topologies/lab.json` — declared topology matching the VOS-Network-Redux design (8 devices, 3 VLANs, all ports and links)
- A CLI entry point or script that instantiates collectors with real MCP device IDs and runs the workflow

**What already exists:**
- `PreflightWorkflow` in `src/vos/apps/preflight/workflow.py` — complete
- `SwitchcraftCollector` in `src/vos/switchcraft/collector.py` — calls MCP gateway
- `OpnsensecraftCollector`, `ProxmoxcraftCollector` — complete
- `merge_observations()`, `verify_topology()`, `trace_vlan_path()` — complete

**Concrete work:**

1. **Create `topologies/lab.json`** — the declared truth for the lab:
   ```
   Devices: opnsense, onti-fe, onti-be, 91tsm, zyxel-gs1900,
            pve-qotom-1u, pve-hx310-db, pve-hx310-arr
   Links: OPNsense ix0 ↔ ONTi-FE port 1 (DAC 10G)
          OPNsense ix1 ↔ ONTi-BE port 1 (DAC 10G)
          ONTi-FE port 2 ↔ 91TSM SFP+ port 1 (DAC 10G)
          ONTi-FE port 8 ↔ Zyxel SFP 1 (fiber 1G)
          ONTi-BE port 7 ↔ HX310-DB eth1 (Cat6+SFP 1G) [EXPECTED DOWN]
          ONTi-BE port 8 ↔ HX310-ARR eth1 (Cat6+SFP 1G) [EXPECTED DOWN]
          91TSM port 8 ↔ HX310-DB eth0 (Cat6 2.5G)
          91TSM port 7 ↔ HX310-ARR eth0 (Cat6 2.5G)
   VLANs: 25 (General), 254 (Management), untagged (Bypass)
   ```

2. **Create `scripts/lab_preflight.py`** — thin script that:
   - Instantiates 4 SwitchcraftCollectors (onti-fe, onti-be, 91tsm, zyxel) with their MCP device IDs
   - Instantiates 1 OpnsensecraftCollector
   - Instantiates 1 ProxmoxcraftCollector (3 nodes)
   - Creates `PreflightWorkflow(topology_path="topologies/lab.json", collectors=...)`
   - Runs `await workflow.run_verification()`
   - Dumps raw observations, merged snapshot, and verification report to `output/`

3. **Fix the MCP device ID mapping** — Switchcraft's registered device IDs need to match what the collector sends. Verify by checking `switchcraft-list-devices` output.

**Expected result:** The verification report will show:
- ONTi-BE ports 7/8: `LINK_DOWN` / `NEIGHBOR_MISSING` (SFP modules missing — known blocker)
- Everything else: should match declared topology
- If mismatches appear beyond the known SFP issue, we've found real drift

**Effort:** Small (1-2 sessions). All pipeline code exists. This is config + glue.

**Acceptance:** `uv run python scripts/lab_preflight.py` produces `output/verification_report.json` with results for all 8 devices.

---

### Phase 2 — Event Persistence + SQLite RunStore

**Goal:** Persist orchestration runs and topology events to SQLite so we have history.

**What needs building:**
- `SqliteRunStore` implementing the existing `RunStore` protocol
- Wire it into the orchestrator as an alternative to `JsonRunStore`

**What already exists:**
- `RunStore` protocol: `src/vos/agentcore/storekit/protocol.py` (save/get/list_runs/delete)
- `RunRecord` model: `src/vos/agentcore/storekit/models.py` (complete audit trail)
- `JsonRunStore`: `src/vos/agentcore/storekit/json_store.py` (working reference implementation)
- Alembic + SQLModel: `alembic/`, `src/vos_workbench/storage/` (infrastructure ready)
- Event bus + EventRecord: `src/vos_workbench/events/` (persistence callback exists)

**Concrete work:**

1. **Create `src/vos/agentcore/storekit/sqlite_store.py`** — implements `RunStore` protocol using SQLModel. The `RunRecord` is already Pydantic — serialize to JSON column in SQLite.

2. **Add Alembic migration** for a `runs` table (id, run_json, created_at, status, domain).

3. **Wire event persistence** — the spine's event bus already has an `on_publish` callback for auto-persistence. Ensure topology events (verification results, collection events) get stored.

4. **Config toggle** — add a config option to select store backend (json vs sqlite). Default: json for dev, sqlite for production.

**Effort:** Small-Medium (1 session). The protocol, models, and DB infrastructure all exist. This is plumbing.

**Acceptance:** After a preflight run, `sqlite3 ~/.vos/runs.db "SELECT count(*) FROM runs"` returns 1. Events queryable via the existing `/api/v1/events` endpoint.

---

### Phase 3 — A770 Executor Registration

**Goal:** Register the local executor and verify the orchestrator selects it with `prefer_local=True`.

**What needs building:** Almost nothing. The code is done.

**What already exists:**
- `LocalExecutor`: `src/vos/agentcore/executorkit/local.py` — complete, tested
  - Points at `http://192.168.254.50:11434/v1` (Ollama on A770)
  - Health check via `/models` endpoint
  - Falls back gracefully when unavailable
  - Tags: `["local", "a770"]`
- `BudgetPolicy.prefer_local`: `src/vos/agentcore/orchestration/budget.py` — done
- `ExecutorRegistry.find_for_task()`: already filters by domain + health

**Concrete work:**

1. **Create a bootstrap script or config** that registers executors at startup:
   ```python
   registry = ExecutorRegistry()
   registry.register(LocalExecutor())  # A770
   registry.register(OpenAICompatibleExecutor(OpenAIExecutorConfig(
       base_url="https://api.anthropic.com/v1",
       model="claude-sonnet-4-20250514",
       api_key_env="ANTHROPIC_API_KEY",
       executor_id="claude-sonnet",
   )))
   ```

2. **Integration test** that verifies: with `prefer_local=True` and A770 reachable, the orchestrator selects `local-a770`. With A770 down, falls back to cloud.

3. **Optional:** If the A770 hardware isn't powered on yet, this phase can be tested with a mock Ollama endpoint or deferred until the machine is set up.

**Effort:** Tiny (< 1 hour). The executor is fully implemented. This is registration + a test.

**Acceptance:** `uv run pytest tests/executorkit/test_local.py -v` passes. Integration test shows correct executor selection.

---

### Phase 4 — First Write Action (VLAN Apply via Switchcraft)

**Goal:** One controlled write operation: apply a VLAN change on a switch with preview, verify, and rollback.

**What needs building:**
- `vos/changekit/` — new module for topology change operations
- contractkit addition: `ChangeApplierProtocol`
- modelkit additions: `ChangeRequest`, `ChangePreview`, `ChangeResult`, `RollbackToken`

**What already exists:**
- Switchcraft MCP tools: `apply-config` with `dry_run`, `config-save`, `config-sync`, `config-status`
- `ImpactRequest`/`ImpactResult` in modelkit (read-side impact preview)
- `SwitchcraftCollector._call_tool()` pattern for calling MCP tools

**Concrete work:**

1. **Add to contractkit:**
   ```python
   class ChangeApplierProtocol(Protocol):
       async def preview(self, request: ChangeRequest) -> ChangePreview: ...
       async def apply(self, request: ChangeRequest) -> ChangeResult: ...
       async def rollback(self, token: RollbackToken) -> ChangeResult: ...
   ```

2. **Add to modelkit:**
   ```python
   class ChangeRequest(BaseModel):
       device: str
       operation: str  # "vlan_assign", "port_enable", etc.
       parameters: dict[str, Any]

   class ChangePreview(BaseModel):
       diff: list[str]         # human-readable diff lines
       commands: list[str]     # actual commands that will be sent
       safe_to_apply: bool
       warnings: list[str]

   class RollbackToken(BaseModel):
       device: str
       pre_state: dict[str, Any]
       timestamp: datetime
   ```

3. **Create `vos/changekit/applier.py`:**
   - `preview()` → calls `switchcraft-apply-config` with `dry_run=true`
   - `apply()` → calls `switchcraft-config-save` (snapshot) → `switchcraft-apply-config` → `switchcraft-device-status` (verify)
   - `rollback()` → calls `switchcraft-config-rollback` to restore git-saved state + `switchcraft-config-sync`

4. **Safety rules (hard):**
   - VLAN 254 (management) and VLAN 1 are NEVER modifiable
   - Bypass network (172.16.0.0/24) is NEVER touched
   - First implementation: ONLY `vlan_assign` operation on non-protected VLANs
   - All changes require `preview()` before `apply()` — enforced in code

5. **Wire into orchestrator:**
   - Register `core.changekit` entry point
   - TopologyExecutor action map: add `"apply": ("POST", "/change/apply")`

6. **Integration test against lab:**
   - Use VLAN 999 (HIL test VLAN from Switchcraft) on a designated test port
   - Create → verify → delete → verify
   - Match Switchcraft's own HIL test lifecycle

**Effort:** Medium (2-3 sessions). New module, but the MCP tools do the heavy lifting.

**Acceptance:** `preview()` returns a diff showing the VLAN change. `apply()` changes the switch. Re-running preflight shows the new VLAN in observations. `rollback()` restores previous state.

---

### Phase 5 — Drift Detection

**Goal:** Compare topology state over time, not just declared-vs-observed at one point.

**What needs building:**
- `vos/driftkit/` — git-aware config comparison engine

**What already exists:**
- Switchcraft `config-status` tool returns IN_SYNC / DRIFT / UNMANAGED / UNREACHABLE
- Switchcraft `config-diff` returns git diff between config versions
- Switchcraft `config-history` returns git log with timestamps
- `verify_topology()` already produces diffs (but point-in-time only)

**Concrete work:**

1. **Add to contractkit:**
   ```python
   class DriftDetectorProtocol(Protocol):
       async def check_drift(self, device: str) -> DriftReport: ...
       async def check_all(self) -> list[DriftReport]: ...
   ```

2. **Create `vos/driftkit/detector.py`:**
   - Calls `switchcraft-config-status` for each managed device
   - For devices with DRIFT: calls `switchcraft-config-diff` to get specifics
   - Enriches with `switchcraft-config-history` to show when drift started
   - Produces `DriftReport` with severity, affected VLANs/ports, last-known-good timestamp

3. **Add modelkit types:** `DriftReport`, `DriftEntry`, `DriftSeverity`

4. **Wire into explorer:** Add `/drift` endpoint in interfacekit routes

**Effort:** Small-Medium (1-2 sessions). Switchcraft does the hard work; driftkit wraps and enriches.

**Acceptance:** `GET /api/v1/drift` returns status for all managed switches. A deliberately changed VLAN shows as DRIFT with specific diff.

---

### Phase 6 — Visualization (Minimum Viable)

**Goal:** See the topology. Even a static render is better than JSON dumps.

**What needs building:**
- Static SVG/HTML output from the topology model
- Or: Mermaid diagram generation from TopologySnapshot

**What already exists:**
- `TopologySnapshot` with all devices, links, VLANs
- `VerificationReport` with all check results
- `Position` model on Device (x, y coordinates)
- graphkit functions (neighbors, bfs, vlan_ports, diagnostics)
- interfacekit with FastAPI routes
- VOS-Network-Redux visualizer spec (D3.js + FastAPI design)

**Concrete work (minimum viable):**

1. **Create `vos/vizkit/mermaid.py`:**
   - Takes `TopologySnapshot` → generates Mermaid graph definition
   - Color-codes devices by type, links by verification status
   - Annotates with VLAN IDs on links

2. **Add interfacekit route:** `GET /api/v1/topology/diagram` → returns Mermaid source or rendered SVG

3. **Optional:** Serve a single-page HTML that renders the Mermaid diagram with pan/zoom

**Effort:** Small (1 session for Mermaid, medium for interactive D3.js)

**Acceptance:** Opening `http://localhost:8000/api/v1/topology/diagram` shows the lab topology with 8 devices, all links, verification status color-coding.

---

## PR Sequence (Revised)

| PR | Phase | Files Changed/Created | Lines (est.) |
|---|---|---|---|
| **#1** | Lab topology + smoke | `topologies/lab.json`, `scripts/lab_preflight.py`, maybe collector config fixes | ~300 |
| **#2** | SQLite store | `src/vos/agentcore/storekit/sqlite_store.py`, migration, config | ~200 |
| **#3** | Executor bootstrap | Config/script for registry setup, integration test | ~100 |
| **#4** | changekit module | `src/vos/changekit/`, contractkit additions, modelkit additions, entry point, tests | ~500 |
| **#5** | driftkit module | `src/vos/driftkit/`, contractkit additions, modelkit additions, tests | ~300 |
| **#6** | Visualization | `src/vos/vizkit/mermaid.py`, interfacekit route, tests | ~200 |

---

## Risk Matrix (Write Operations — Phase 4)

| Risk | Impact | Mitigation |
|---|---|---|
| Wrong VLAN applied | Network disruption | `dry_run=true` preview mandatory before every apply. VLAN 254/1 hardcoded as immutable. |
| Partial failure | Inconsistent state | Switchcraft's `config-save` snapshots pre-state. `config-rollback` + `config-sync` restores. |
| SFP issue masks real drift | False negatives | Mark ONTi-BE ports 7/8 as `expected_down` in lab topology until SFP modules installed. |
| MCP gateway down | Collection fails | `SwitchcraftCollector.check_health()` already handles this. Preflight reports partial collection. |
| A770 cold start | Slow orchestration | `LocalExecutor.health()` returns "error" when unavailable. Registry auto-falls back to cloud. |
| Concurrent manual changes | Config conflict | Switchcraft `apply-config` checks current state at apply time, aborts on unexpected diff. |

---

## What ChatGPT Got Right

- Phase ordering (read → memory → executor → write → drift → viz)
- Rollback token concept
- Risk matrix structure
- The overall "eyes, memory, brains, hands" framing

## What This Plan Fixes

- File paths that actually exist
- Modules that don't need to be built (they're done)
- Effort estimates based on real code (A770 executor: "tiny" not "high")
- Phase 5 replaced: "unify orchestration APIs" (non-problem) → drift detection (real gap)
- Concrete device IPs, VLAN numbers, port assignments from the actual lab
- Switchcraft MCP tool names that actually exist on localhost:4444
- Dependency rules and naming conventions that match CLAUDE.md

---

*This plan should be read alongside:*
- *Architecture spec:* `docs/superpowers/specs/2026-04-07-ruggensgraat-architecture-design.md`
- *Options catalog:* `docs/OPTIONS-AND-MODULES.md`
- *Lab topology source:* `~/git/VOS-Network-Redux/docs/superpowers/specs/2026-04-01-vos-network-redux-design.md`
- *North Star:* `~/git/vos-docs/docs/architecture/VOS-NORTH-STAR.md`
