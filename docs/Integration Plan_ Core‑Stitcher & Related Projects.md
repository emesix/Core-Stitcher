# Integration Plan: Core‑Stitcher & Related Projects

Core‑Stitcher has a robust architecture and test coverage, but key capabilities remain unimplemented. Most missing pieces already exist in sibling projects (Switchcraft, Homelable, INTELL‑A770, VOS‑Network‑Redux, ONT device profiles). This plan proposes concrete reuse and integration steps to close gaps in **write path**, **live integration**, **orchestrator memory**, **local executor**, **visualization**, and **deployment**. Key points:

- **Live Lab Proof:** First, wire up Core‑Stitcher’s read pipeline to actual hardware (ONTI switch, OPNsense, Proxmox) and capture raw data. This validates collectors and the topology model. (E.g. reuse Homelable’s network scan scripts【42†L333-L342】.)  
- **Persistence/Memory:** Introduce a `RunStoreProtocol` and SQLite-backed store (in addition to the dev JSON store) to record runs, tasks, and results. A SQLite RunStore (like DeepAgents’ RunStore) is a proven pattern【28†L27-L28】.  
- **Local Executor:** Register the INTELL‑A770 AI executor (tagged `local`) in the orchestrator. Core‑Stitcher’s `BudgetPolicy` already supports preferring local executors. Ensure the executor advertises its capabilities (summary, review) and is health-checked.  
- **First Write Action:** Implement a *safe* remediation action (e.g. “apply VLAN on switch”) with preview, commit, verify, and rollback. Only one narrow operation is needed to break the read-only ceiling, minimizing risk.  
- **Orchestration Unification:** Refactor the API layer so that `/execute` and `/review` routes both invoke a single orchestration service. This avoids diverging logic and keeps policy, task logging, and review in one code path.  
- **Visualization and Docs:** Leverage the VOS‑Network‑Redux visualization spec for a future UI. For now, focus on accessible output (e.g. static SVG) and clear operator documentation (deployment guides, runbooks). Use Twelve-Factor principles: containerize with a `Dockerfile`, externalize config, add health checks【54†L10-L19】【55†L168-L174】.

In sum, reuse existing modules for discovery (Homelable), network action (Switchcraft), and local AI (A770), then implement minimal new glue. This will turn Core‑Stitcher from “read-only brain” into a working agent with *eyes (real data), memory (SQLite), reasoning (AI loop), and one hand (a VLAN apply). 

## Reuse Mapping

| Repo / Component      | Harvest & Reuse                          | Key Files/Modules (example paths)       | Effort  |
|-----------------------|------------------------------------------|-----------------------------------------|---------|
| **Core‑Stitcher (current)** | Base system (collect/merge/verify pipeline, config loading, tests)【42†L333-L342】. | Topology loaders, `CollectKit`, `VerifyKit`, orchestrator classes. | — (baseline) |
| **Switchcraft**       | **Write path modules**: VLAN and port configuration via MCP. (Core‑Stitcher’s `SwitchcraftCollector` already calls MCP commands: device-status, get-ports, get-vlans.) Reuse code for applying configs. | *e.g.* `switchcraft/vlan.py`, `switchcraft/ports.py` (HTTPX calls); `switchcraft/commands.py` for `device-config-apply`.  | Med (wiring into Core‑Stitcher) |
| **Homelable**        | **Discovery & visualization**: Network scanning (nmap), pending-device queue, and MCP AI server from Homelable are direct analogues. Reuse scanning logic and consider the UI (canvas) concepts.  | *e.g.* `homelable/backend/scripts/run_scan.py` (nmap scanner)【42†L333-L342】; `backend/src` for status checks; `frontend/src/Diagram.tsx` (canvas).  | Low (import scanning code) |
| **INTELL‑A770**      | **Local inference executor**: Code to run LLMs or models on local hardware (tagged `local`). Reuse model-loading and execution patterns.  | *e.g.* `intell_a770/executor.py`, `intell_a770/models/*` for loading GPT-style models. | High (integrating heavy ML code) |
| **VOS‑Network‑Redux** | **Visualizer spec**: Network diagram UI spec (JSON or data format) for rendering topology. Reuse spec definitions and styles for future UI. | *e.g.* `vos_network_redux/spec/diagram.json` (layout definitions), `schema/*.json` for node/edge shapes. | Low (design reuse) |
| **ONT Projects**     | **Device profiles/adapters**: Modules for ONTI switch, OPNsense, Proxmox. E.g. MCP adapters (`opnsensecraft`, `proxmoxcraft` etc). Reuse device schemas (interfaces, JSON models) and collectors. | *e.g.* `opnsensecraft/client.py`, `opnsensecraft/model.py`; `proxmoxcraft/api.py`; `onticraft/device.py`. (Exact paths TBD) | Med (reuse code + config) |
| **Other (merged) repos** | **Patterns** from Ruggensgraat, Project-Explorer, etc.: Already merged. Remaining overlap: none critical.   | - | - |

*Notes:* We assume Switchcraft, INTELL‑A770, ONT codebases exist but paths are examples. Where details are unavailable, we mark as unspecified. For every reuse, compatibility must be verified (e.g. data models from Switchcraft must match Core-Stitcher’s).

## Architecture Diagram

```mermaid
graph LR
  subgraph Core_Stitcher
    Tpl[Declared Topology] --> Collectors[Collectors Stage]
    Collectors --> Merger[Merge Stage]
    Merger --> Verifier[Verify Stage]
    Verifier --> Impact[Impact Analysis]
  end
  subgraph Orchestrator
    Impact --> Review[Plan/Review Loop]
    Review --> RunStore[RunStore (SQLite)①]
    Review --> LocalExec[Local Executor (A770)②]
    RunStore --> History[(Execution Log)]
    LocalExec --> History
  end
  subgraph Remediation
    Review --> Apply[VLAN Apply (Remediate)]
    Apply --> Devices[Lab Devices (Switch/OPNsense/Proxmox)]
    Switchcraft -.-> Apply  <!-- Switchcraft code drives this -->
  end
  HomelableScanner[Homelable Scanner③] -.-> Collectors
  VOS_Spec[Visualizer Spec (VOS)] -.-> VisualizationUI[UI/Diagram Component④]
  style RunStore fill:#eef,stroke:#333,stroke-width:1px
```

1. **RunStore (SQLite)**: new persistence store for runs/tasks (adds memory).  
2. **Local Executor (A770)**: selects local AI model for plan/review.  
3. **Homelable Scanner**: network discovery, pushes raw data into Collectors (reused logic from Homelable【42†L333-L342】).  
4. **Visualization UI**: future work using VOS‑Network‑Redux diagram spec.

*Legend:* Solid arrows show core data flows. Dashed lines (`-.->`) indicate components being reused/integrated (Homelable, Switchcraft, VOS).  

## Implementation Roadmap

We break the work into **6 phases** (roughly prioritized by impact). Phases 1–4 have concrete code deliverables; Phases 5–6 are refinement and docs.

1. **Phase 1 – Live Read-Path Validation:** Wire up Core-Stitcher to actual lab devices.
   - **Goals:** Run `PreflightWorkflow` (declared→collect→merge→verify) against one real switch, one OPNsense, one Proxmox. Dump all raw and normalized data.  
   - **Actions:** 
     - Add a “smoke test” command (e.g. `core_stitcher preflight --topology lab.yaml --output run1/`) that invokes collectors and writes artifacts.  
     - Persist: raw adapter JSON, normalized observations, merged snapshot, and verify report to disk.  
     - Ensure concurrent collection works (already uses `asyncio.gather`).  
   - **Key Changes:** 
     - `core_stitcher/cli.py` (new command), 
     - Modify `SwitchcraftCollector` and others to allow live run (likely none, already implemented).  
   - **Acceptance:** Data files are produced; `verifyStage` reports fetched, matching known config. (Example command: 
     ```bash
     python -m core_stitcher preflight --topology lab_topology.yaml --store raw_dump/
     ```
     should complete without errors against real devices.)

2. **Phase 2 – Orchestrator Memory (RunStore):** Introduce persistent storage for runs.
   - **Goals:** Define `RunStoreProtocol`; implement SQLite-backed store. Write execution logs and summaries to DB.  
   - **Actions:** 
     - Create `RunStoreProtocol` interface (methods: `save_run`, `get_runs`, etc.).  
     - Retain `JsonRunStore` for dev/demo, but add `SqliteRunStore` (uses `sqlite3` or SQLAlchemy).  
     - Define tables: runs, tasks/steps, reviewers.  
     - Modify orchestrator to call `store.save_run()` at start and finish of a run, and to log each step and review outcome.  
     - Provide query helpers (e.g. “last failures for device”).  
   - **Key Changes:** 
     - New file `core_stitcher/run_store.py` (protocol + classes); 
     - Update `agentcore/orchestrator.py` to use `RunStore` instead of plain JSON.  
   - **Acceptance:** Unit tests confirm persistence: after a run, DB has one run row, step rows matching workflow. (E.g. Python test to open SQLite DB and query tables.)

3. **Phase 3 – Local AI Executor (INTELL‑A770):** Hook up the local inference engine.
   - **Goals:** Register the A770-backed executor in AgentCore, ensuring `BudgetPolicy` can pick it (`prefer_local=true`). Provide health-check endpoint.  
   - **Actions:** 
     - Define new executor entry in config or code: tag `local`, no domain restriction.  
     - Integrate INTELL‑A770 code: likely a separate service or library. For now, stub a “local LLM” that returns canned plan.  
     - Update `_find_ai_executor()` and service registry (could extend `agentcore/registry.py`).  
     - Expose a simple HTTP health endpoint (or rely on executor library).  
     - Ensure executor can run summary/correct steps on local hardware.  
   - **Key Changes:** 
     - `agentcore/executors.py` (register A770 executor class), 
     - `config.yaml` or similar (add executor entry), 
     - `api/misc.py` (health route for local executor).  
   - **Acceptance:** A run specifying `--prefer-local` should choose the A770 executor (monitor logs or debug). The executor responds within budget (e.g. sub-1min if mocked).  

4. **Phase 4 – First Remediation Action:** Implement a controlled write operation.
   - **Goals:** Add one real “apply config” operation (VLAN change on a switch) with dry-run and rollback support.  
   - **Actions:** 
     - Define new API: e.g. `ApplyRequest {domain, device, operation}`, and models `ApplyPreview`, `ApplyResult`, `RollbackToken`.  
     - Implement `ApplyCommand` in a new module (e.g. `remediatekit` or extend `SwitchcraftAgent`).  
     - Workflow: 
       1. **Preview:** Check declared state diff (simulate `switch-vlan-assign`).  
       2. **Apply:** Push change via MCP (`switchcraft/commands.set-vlan`).  
       3. **Verify:** Re-collect that switch’s state and confirm VLAN changed.  
       4. **Rollback:** If verify fails (or on request), reapply old VLAN from captured pre-state (RollbackToken holds previous config).  
     - Ensure all steps are logged and part of RunStore (tie into orchestrator steps and reviews).  
   - **Key Changes:** 
     - New files: `core_stitcher/apply_request.py` (data models), 
     - `remediatekit/apply_vlan.py` (implementation), 
     - Hook into orchestrator to allow remediation tasks (maybe add `remediate()` workflow path).  
   - **Acceptance:** In integration test or lab, performing the apply command on a test switch actually changes its VLAN. If we interrupt mid-change (simulate failure), the VLAN is restored. Example: use a test Netbox/virtswitch or real test port.

5. **Phase 5 – Unify Orchestration APIs:** Consolidate execute/review endpoints.
   - **Goals:** Ensure the HTTP API (or CLI) uses one common orchestration flow. Remove ad-hoc branches.  
   - **Actions:** 
     - Refactor `project_stitcher/api.py` so both `/execute` and `/review` call the same service methods.  
     - Ensure executor selection, RunStore logging, and budget policy are not duplicated.  
     - Possibly add a service layer (`core_stitcher/service.py`) that both CLI and HTTP use.  
   - **Key Changes:** 
     - Edit `api.py` (remove any direct orchestrator logic, call orchestrator module), 
     - Consolidate config loading (only one parser).  
   - **Acceptance:** Running via CLI and via HTTP yield identical behavior/logging. Existing tests still pass after refactor (CI catches any divergence).

6. **Phase 6 – Visualization & Documentation:** Polish UI and docs.
   - **Goals:** Improve the Explorer/static UI (if any) and write operator guides.  
   - **Actions:** 
     - Hardening: In “interfacekit”, refine `/explorer/ui` static SVG (presently a stub) using VOS‑Redux spec; or at least display the model as text.  
     - Write documentation: 
       - **Operator Guide:** Steps to deploy (dependencies, Docker, systemd), how to run preflight, how to read logs/results.  
       - **API Docs:** Detailed spec of `ApplyRequest/Result`, `PreflightRequest/Report`.  
       - **Deployment Guide:** Example `docker-compose.yml` or `systemd` service file, health-check endpoints (e.g. `/health`). Emphasize config via ENV (Twelve-Factor)【54†L10-L19】.  
       - Provide a “Runbook” for common tasks (run smoke, apply config, rollback).  
   - **Key Changes:** 
     - Possibly `interfacekit/static` (frontend code), 
     - new `docs/` markdown files, `README.md`.  
   - **Acceptance:** A new team member can follow the README to install and run a lab preflight. The explorer page shows the network (even a static image counts). 

### Early PR Breakdown (First 3 PRs)

**PR #1: Live Read-Path Smoke & Persistence Stub**  
- **Files:** 
  - `core_stitcher/cli.py`: Add `preflight` command entry.  
  - `core_stitcher/preflight_workflow.py`: (if not existing) implement a run that loops collectors→merge→verify and writes output to files.  
  - `core_stitcher/run_store.py`: Introduce `RunStoreProtocol` interface (no-op save).  
  - `core_stitcher/utils.py`: Helpers to dump JSON (raw/merged/verify).  
- **Changes:**  
  - Captures raw adapter output: modify each collector to optionally write raw JSON.  
  - Logging: ensure `preflight` prints summary and paths.  
- **Outcome:** `python -m core_stitcher preflight` works, producing a structured artifact directory.  

**PR #2: SQLite RunStore and Logging**  
- **Files:** 
  - `core_stitcher/run_store.py`: Implement `SqliteRunStore` (tables: runs, tasks, reviews).  
  - `agentcore/orchestrator.py`: Inject `RunStore` usage (create run, log steps, finish run).  
  - `core_stitcher/settings.py`: Config option to choose store type.  
- **Changes:** 
  - Database schema migration: code to initialize DB.  
  - Replace any `JsonRunStore` calls with protocol calls.  
- **Outcome:** After running a workflow, the `.sqlite3` file has records. Unit tests confirm queries (e.g. listing runs).

**PR #3: Register Local Executor (A770)**  
- **Files:** 
  - `agentcore/executors.py`: Add `A770Executor` class and tag `local`.  
  - `core_stitcher/config.yaml`: Add executor entry (path/alias).  
  - `agentcore/health.py`: (optional) add health endpoint for A770 service.  
- **Changes:** 
  - Modify `RunOrchestrator._find_ai_executor()` or registry to include new executor from config.  
  - Update selection policy: ensure `prefer_local = true` is passed through budget policy.  
- **Outcome:** Test that `orchestrator.run` uses `A770Executor` (e.g. in logs or by mocking it).  

Later PRs (outline only): Implement `ApplyRequest` and `remediatekit` (Phase 4), API unification (Phase 5), UI/docs (Phase 6).

## Test Plan & Acceptance

We propose layered testing for each phase:

- **Unit Tests:** Extend existing coverage. For new code (RunStore, Apply logic, executor), write unit tests. For example, test saving/loading runs to SQLite; test the VLAN diff algorithm in `apply_vlan.py`; test executor selection logic.

- **Integration Tests (emulated):**  
  - **Collectors:** Use known JSON fixtures or a dockerized ONT switch emulator; assert `collect()` returns expected port/VLAN data.  
  - **Preflight Workflow:** Simulate a small topology file (YAML) and verify the end-to-end output. Could mock external calls for now, or use a staging test switch.  
  - **RunStore:** Create a fake run (via API), then query the DB to check results.  
  - **Executor:** Mock LLM calls; verify the orchestrator respects the `prefer_local` flag.  
  - **Apply Operation:** In a controlled test (or staging switch), change a VLAN, then simulate failure and check rollback restored the original VLAN. Possibly use a virtual switch (e.g. Cisco VIRL) or dummy network simulator.

- **Live Lab Smoke:** The key acceptance for Phase 1. A script like:
  ```bash
  core_stitcher preflight --topology mylab.yaml --output logs/run1
  ```
  should collect from at least one real device of each type. Check that `logs/run1/raw/`, `normalized/`, `merged.json`, and `verify.json` exist. Manually verify values against device config.

- **Property & Stress Tests (future):**  
  - Add property-based tests (e.g. fuzz various topologies) and mutation testing as noted (currently missing).  
  - Run resource stress tests: measure performance of `collect()` on many devices.  

Each phase requires its own “Definition of Done.” For example, Phase 4 is not done until an actual device reflects the config change and a rollback undoes it. For phased acceptance, see table below:

| Phase | Testing (Unit/Int) | Lab (Live) Acceptance |
|---|---|---|
| 1. Live Read-Path | Unit tests for new CLI output; CI with dummy topology. | Preflight on lab yields collected data (ports, VLANs) matching devices. |
| 2. RunStore | Unit tests on `SqliteRunStore`; integration test to write/read a run. | After running workflow, open the SQLite DB and confirm entries (runs, tasks). |
| 3. Local Executor | Unit test that executor can be instantiated; CI pipeline to ensure selection code runs. | Run with prefer-local: logs show A770 used (or measure a local GPU model call). |
| 4. Apply VLAN | Unit tests: compute VLAN diff, simulate rollback logic. | On a test switch, `ApplyRequest` changes a port’s VLAN; simulated failure triggers rollback, restoring original VLAN. |
| 5. Unified Orchestration | Regression tests to ensure existing flows still work. | API vs CLI produce same results; run a workflow via both and diff outputs. |
| 6. Visualization & Docs | Proofread docs; lint markdown; ensure the explorer UI loads. | Another developer follows README/deployment guide successfully; visual network map displays. |

## Risk & Rollback Matrix (Write Operations)

Implementing writes introduces risks. We mitigate with dry-runs and rollback tokens. A few key risks:

- **Wrong Config Applied:** *Impact:* Misconfigured network (outage). *Mitigation:* Always perform a **dry-run preview** (compare intended vs current state). Only apply if preview matches expected change. Use conservative ACLs or test devices first.  
- **Partial Failure During Write:** *Impact:* Device left in inconsistent state. *Mitigation:* **Atomic sequence with rollback**: capture pre-change state (RollbackToken) before applying. If any error or mismatch, immediately revert using RollbackToken (restoring exact prior config).  
- **Executor Failure / Stale State:** *Impact:* Orchestrator thinks change succeeded when it didn’t. *Mitigation:* After apply, always **re-collect and verify** device state. If verify step fails or times out, trigger rollback and mark run as failed.  
- **Concurrent Changes:** *Impact:* Concurrent manual changes could conflict with automated action. *Mitigation:* Check **current state at apply time**; abort if unexpected diff found. Locking or transaction semantics (if device supports) are ideal.  
- **Schema/Protocol Mismatch:** *Impact:* Write payload format could change (e.g. devices upgrade). *Mitigation:* Version your ApplyRequest/Result contracts. Use well-tested libraries (Switchcraft) to encode config changes.

In case of failure, every Apply operation should produce a **RollbackToken** containing enough data to undo the change. For example, for VLAN apply, RollbackToken includes the original VLAN and port. Rolling back then simply reapplies that original configuration.

Finally, follow best practices (see Twelve-Factor App) for deployment and monitoring【54†L10-L19】【55†L168-L174】. For example, include a **healthcheck** in Docker (e.g. `HEALTHCHECK CMD curl --fail http://localhost:8000/health`)【55†L168-L174】, run behind a supervisor (systemd), and log extensively so issues can be diagnosed quickly.

---

*Sources:* Core-Stitcher and related repo documentation (e.g. Homelable README for discovery【42†L333-L342】, MCP overview【43†L71-L79】, RunStore API【28†L27-L28】, Docker best-practices【55†L168-L174】) and architectural best practices (Twelve-Factor【54†L10-L19】).