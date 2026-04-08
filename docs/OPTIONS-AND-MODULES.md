# Core-Stitcher: Options & Modules from the Ecosystem

> Generated 2026-04-08 by auditing all 30+ projects in ~/git/
> Purpose: catalog ideas, patterns, and modules that can be harvested from older projects into Core-Stitcher.

---

## Current State Summary

Core-Stitcher is a production-ready monorepo with:
- **Spine** (vos_workbench): runtime, config, events, storage, registry, SDK, API
- **Topology domain** (network-stitcher): contractkit, modelkit, graphkit, storekit, 3 adapters (switchcraft, opnsensecraft, proxmoxcraft), 3 engines (collectkit, verifykit, tracekit), interfacekit, 2 app shells (preflight, explorer)
- **AI orchestrator** (project-stitcher): agentcore with taskkit, executorkit, plannerkit, reviewkit, storekit, orchestration, registry, 1 app shell (project_stitcher)
- **Stats**: ~7,654 LOC implementation, ~11,264 LOC tests, 67 test files, 0 TODOs

---

## A. New Domain Capability Packs (Layer B)

These are entirely new domain packs that follow the same pattern as the topology domain.

### A1. Searchcraft Domain Pack
**Source:** `~/git/Searchcraft`
**Status:** Scaffolded, not implemented
**What it adds:** Deep research agent — concurrent search across 10+ sources (Google, arXiv, Reddit, GitHub, Wayback, Tor/I2P, FTP, Telegram, Pastebin), finding dedup + reliability scoring, LLM synthesis with source attribution.
**Architecture:** Provider-adapter pattern (each source is a pluggable provider). Designed from day one as a VOS Layer B capability pack.
**Modules needed:**
- `vos/searchcraft/` — provider adapters (one per source)
- `vos/searchcraft/synthesizer.py` — LLM-based result synthesis
- `vos/searchcraft/scorer.py` — reliability scoring
- contractkit additions: `SearchProtocol`, `SynthesizerProtocol`
- modelkit additions: `SearchRequest`, `SearchResult`, `Finding`, `SynthesisReport`
**Effort:** Medium-Large
**Value:** When project-stitcher needs to research infrastructure decisions, it dispatches to searchcraft. Closes the "intelligence gathering" gap in the orchestrator.

### A2. Docflow Domain Pack
**Source:** `~/git/docflow-mcp`
**Status:** Working MCP server (Gitea + Wiki.js)
**What it adds:** Documentation workflow — create topics as Gitea issues, decompose into parts, track draft/review/ready/published state, cross-link via keywords, preview structure, publish to Wiki.js.
**Architecture:** Multi-adapter (Gitea for CMS, Wiki.js for publishing), label-based state machine, context tracking.
**Modules needed:**
- `vos/docflowcraft/` — Gitea + Wiki.js adapters
- contractkit additions: `DocumentWorkflowProtocol`
- modelkit additions: `Topic`, `Part`, `PartStatus`, `PublishResult`
**Effort:** Medium (existing MCP server is functional, needs domain-pack wrapping)
**Value:** Closes the "documentation as code" loop — the orchestrator can create, review, and publish docs as part of project workflows.

### A3. Discovery Domain Pack
**Source:** `~/git/homelable`
**Status:** Working FastAPI app with React frontend
**What it adds:** Network topology discovery via nmap scanning, device classification, pending device queue for human approval, health status monitoring (ping/TCP/HTTP/SSH/Prometheus).
**Modules needed:**
- `vos/discoverycraft/` — nmap wrapper, device classifier, health checker
- contractkit additions: `DiscoveryProtocol`, `HealthCheckProtocol`
- modelkit additions: `DiscoveredDevice`, `HealthStatus`, `HealthCheckResult`
**Effort:** Medium
**Value:** Currently Core-Stitcher's topology is declared (JSON). Discovery would enable semi-automated topology ingestion — discover what's on the network, present for approval, merge into declared topology.

---

## B. Adapter Module Expansions

New adapter modules for existing domain patterns. These follow the established `resource.*` pattern.

### B1. ONTI Switch Adapters (3 variants)
**Source:** `~/git/ONT-S207CW-62TS-SE`, `~/git/ONT-S207CW-91TSM`, `~/git/ONT-S508CL-8S`
**What it adds:** Device-specific collectors for the three ONTi switch models in the lab.
**Details per device:**
| Model | SoC | Interface | Access | VLAN Quality |
|-------|-----|-----------|--------|--------------|
| S207CW-62TS-SE | RTL8373 | Web CGI API | HTTP | Full 802.1Q |
| S207CW-91TSM | RTL8372N | Web CGI API | HTTP | Weak (port-group only) |
| S508CL-8S | RTL930x | Cisco IOS CLI | Telnet/Serial | Full 802.1Q |
**Modules needed:** These would be device profiles/drivers within switchcraft, not separate modules. Add device_slug normalization for each.
**Effort:** Small per device (normalizer + collector config)
**Value:** Enables live collection from all lab switches. The S508CL-8S is particularly rich (MAC table, transceiver diagnostics, SFP power levels).

### B2. SFP/Transceiver Diagnostics
**Source:** `~/git/ONT-S508CL-8S` (transceiver detail data)
**What it adds:** Optical signal monitoring — RX/TX power (dBm), temperature, voltage, alarm flags per SFP port.
**modelkit additions:** `TransceiverDiagnostics(rx_power_dbm, tx_power_dbm, temperature_c, voltage_v, alarm_flags)`
**Observation type:** `port_optical_signal`
**Effort:** Small (data model + collector extension)
**Value:** Physical layer health monitoring. Detect degrading fibers/DACs before they cause link flaps.

### B3. Zabbix Adapter
**Source:** MCP Gateway (zabbix tools already available), `~/git/VOS-Network-Failed` (Zabbix deployed)
**What it adds:** Pull monitoring data from Zabbix — host status, item values, trigger states, problems.
**Modules needed:**
- `vos/zabbixcraft/` — Zabbix API collector via MCP gateway
- contractkit additions: `MonitoringProtocol`
- modelkit additions: `MonitoringStatus`, `AlertState`, `MetricValue`
**Effort:** Medium
**Value:** Correlate topology verification with monitoring state. "Link is down" (verifykit) + "Zabbix trigger fired 2 min ago" (zabbixcraft) = richer diagnostics.

### B4. WiFi/AP Adapter
**Source:** `~/git/VOS-Network-Failed` (RT2980 APs, 3 SSIDs), `~/git/VOS-Network-Redux` (WiFi Phase 4 plan)
**What it adds:** Collect wireless AP state — SSIDs, connected clients, signal strength, channel utilization.
**Modules needed:**
- `vos/wificraft/` — AP collector (likely via SNMP or SSH)
- modelkit additions: `AccessPoint`, `WirelessClient`, `RadioState`
**Effort:** Medium-Large (depends on AP management interface)
**Value:** Extends topology from wired-only to wireless. "VLAN 110 serves SSID home-wifi, currently 12 clients" enriches the topology picture.

---

## C. Engine Module Expansions

New capabilities that process/analyze topology data.

### C1. Drift Detection Engine
**Source:** `~/git/switchcraft` (git-versioned desired state + drift detection)
**What it adds:** Compare current device configs against git-committed desired state. Detect configuration drift over time, not just declared-vs-observed at a point in time.
**Modules needed:**
- `vos/driftkit/` — git-aware config comparator
- contractkit additions: `DriftDetectorProtocol`
- modelkit additions: `DriftReport`, `DriftEntry`, `DriftSeverity`
**Effort:** Medium
**Value:** verifykit answers "does reality match the plan?" — driftkit answers "has reality changed since last check?" Temporal dimension to verification.

### C2. Change Planner Engine
**Source:** `~/git/switchcraft` (HIL testing + desired state sync), `~/git/OG-HomeLab-Net-Orchistrator_MCP` (intent-based config)
**What it adds:** Given a desired topology change, generate the exact commands needed per device, preview diff, apply with rollback.
**Modules needed:**
- `vos/changekit/` — intent→command translator, diff previewer, apply/rollback engine
- contractkit additions: `ChangePlannerProtocol`
- modelkit additions: `ChangeIntent`, `ChangePlan`, `CommandSequence`, `RollbackPoint`
**Effort:** Large (vendor-specific command generation)
**Value:** Closes the loop from "detect problem" to "fix problem". Currently Core-Stitcher can verify and trace but not remediate. This adds the write path.

### C3. Topology Visualizer Engine
**Source:** `~/git/VOS-Network-Redux` (network-topology-visualizer-design.md), `~/git/homelable` (canvas-based visualization)
**What it adds:** D3.js/canvas-based interactive topology map. Render devices, links, VLANs with color coding. Overlay verification results, trace paths, impact zones.
**Modules needed:**
- `vos/vizkit/` — graph layout computation, SVG/JSON export
- interfacekit additions: static asset serving, WebSocket for live updates
- modelkit additions: `Position` already exists, add `LayoutHints`, `VisualOverlay`
**Effort:** Large (frontend + layout algorithms)
**Value:** The "show me" capability. Everything else in Core-Stitcher is data/API — this makes it visual. The VOS-Network-Redux spec already has a D3.js + FastAPI design.

### C4. Compliance Checker Engine
**Source:** `~/git/VOS-Network-Redux` (CIS IG1 compliance mapping from day one)
**What it adds:** Map topology state to compliance frameworks (CIS Controls v8, etc.). Check: segmentation, default credentials, management access controls, encryption.
**Modules needed:**
- `vos/compliancekit/` — rule engine with framework-specific rulesets
- contractkit additions: `ComplianceCheckerProtocol`
- modelkit additions: `ComplianceReport`, `ControlMapping`, `ComplianceFinding`
**Effort:** Medium
**Value:** Answers "is my network compliant?" not just "is my network correct?" Different audiences (security vs. ops).

---

## D. Executor Expansions (Layer C)

New executor implementations for the AI orchestrator.

### D1. INTELL-A770 Local Executor
**Source:** `~/git/INTELL-A770`
**Status:** Spec exists, physical hardware available (2x Intel Arc A770 GPUs)
**What it adds:** On-premises LLM inference via OpenAI-compatible API. Cold-start aware, health-monitored, auto-fallback to cloud.
**Modules needed:**
- Implement `executorkit.local.LocalExecutor` fully (skeleton exists)
- Health endpoint integration, model selection, cold-start handling
**Effort:** Medium (runtime already scaffolded in Core-Stitcher)
**Value:** Private inference for sensitive topology data. No data leaves the lab. Budget policy: `prefer_local=True, allowed_tiers=[LOCAL, CHEAP]`.

### D2. Automaker-Style Worktree Executor
**Source:** `~/git/automaker` (Claude Agent SDK + git worktrees for isolated feature development)
**What it adds:** An executor that works in isolated git worktrees — plan, execute code changes, review, merge. Full feature→plan→execute→review→correct loop.
**Architecture from automaker:**
- React+Electron frontend, Express backend, WebSocket streaming
- Feature → Plan → Execute → Review → Correct pipeline (mirrors Core-Stitcher's orchestration exactly)
- Git worktree isolation per feature
**Modules needed:**
- `executorkit.worktree.WorktreeExecutor` — git worktree lifecycle + code execution
**Effort:** Large
**Value:** Enables the orchestrator to make code/config changes in isolation, review them, then merge. Infrastructure-as-code meets AI orchestration.

---

## E. Spine Enhancements

Features from VOS-Workbench-standalone that aren't yet in Core-Stitcher.

### E1. Memory Model (4-Layer Hierarchy)
**Source:** `~/git/VOS-Workbench-standalone` (docs/architecture/memory-model.md)
**What it adds:** Session → Working → VOS → Archive memory with promotion pipeline. Session memory is ephemeral (per-run), working memory persists across runs, VOS memory is shared across projects, archive is immutable history.
**Effort:** Medium
**Value:** The orchestrator currently has no memory between runs. Adding memory layers enables learning: "last time we verified this topology, these issues were found."

### E2. Policy Engine
**Source:** `~/git/VOS-Workbench-standalone` (architecture docs), `~/git/switchcraft` (HIL safety constraints)
**What it adds:** Rule-based policy evaluation with priority ordering, first-match-wins. Gate dangerous operations, enforce constraints, audit policy decisions.
**Effort:** Medium
**Value:** "Never apply changes to VLAN 254 (management)" as a policy rule, enforced before any changekit operation.

### E3. Settings Layer Source Tracing
**Source:** `~/git/VOS-Workbench-standalone` (config/merge.py)
**What it adds:** Track which config layer (managed/bootstrap/project/local/runtime) set each value. Enables "why is this configured this way?" debugging.
**Effort:** Small
**Value:** Config debugging. When a module behaves unexpectedly, trace the config value to its source.

### E4. Event Persistence to SQL
**Source:** `~/git/VOS-Workbench-standalone` (storage/models.py — EventRecord, event persistence)
**What it adds:** Persist events to SQLite with type/source/severity indexing. Query historical events via API with pagination/filtering.
**Current state:** Core-Stitcher has event bus but unclear if events are persisted.
**Effort:** Small (Alembic + SQLModel already in place)
**Value:** Audit trail. "When did VLAN 200 last fail verification?" requires persistent events.

---

## F. Cross-Cutting Patterns Worth Adopting

These aren't modules but architectural patterns proven in other projects.

### F1. Git-Versioned Desired State
**Source:** `~/git/switchcraft`
**Pattern:** Store desired device configs in git. Every change is a commit. Drift = diff between HEAD and live state.
**Applies to:** storekit (topology JSON → git-tracked), driftkit (git diff for change detection)

### F2. Intent-Based Configuration
**Source:** `~/git/OG-HomeLab-Net-Orchistrator_MCP`
**Pattern:** Declare WHAT you want (VlanIntent, PortIntent), not HOW to achieve it. System generates vendor-specific commands.
**Applies to:** changekit (intent → command translation)

### F3. HIL Testing with Safety Constraints
**Source:** `~/git/switchcraft`
**Pattern:** Test changes on real hardware with guardrails — designated test VLANs, designated ports, snapshot-apply-verify-cleanup lifecycle.
**Applies to:** changekit (safe apply), policy engine (constraint enforcement)

### F4. Multi-Source Metadata Enrichment
**Source:** `~/git/Gamarr` (IGDB + ScreenScraper), `~/git/openWRT-Forum-extraction-MCP`
**Pattern:** Combine data from multiple sources, deduplicate, enrich with metadata. Gamarr does this for game metadata; topology can do this for device data.
**Applies to:** collectkit (already merges observations — extend with metadata enrichment)

### F5. State Machine Workflows
**Source:** `~/git/docflow-mcp`
**Pattern:** Enum-based status tracking with explicit transitions. draft→review→ready→published.
**Applies to:** Orchestration run states, change request lifecycles

### F6. Bypass-Always-Works Principle
**Source:** `~/git/VOS-Network-Redux` (172.16.0.0/24 emergency backdoor)
**Pattern:** Always maintain an out-of-band access path that no automation can modify.
**Applies to:** Policy engine rule: "VLAN 254 and 172.16.0.0/24 are immutable, reject all changes"

---

## G. Device Model Enrichments

Data models informed by hardware reverse engineering.

### G1. Realtek Switch Family Profiles
**Source:** ONT projects (3 devices)
**Add to modelkit:**
```
DeviceProfile:
  soc: str              # "rtl8373", "rtl8372n", "rtl930x"
  management_protocol: str  # "web-cgi", "cisco-cli", "openwrt-uci"
  vlan_isolation: str   # "strict-802.1q", "port-group-weak"
  firmware_version: str
  known_vulnerabilities: list[str]  # e.g., "reflected-xss-alert-cgi"
```

### G2. Transceiver Diagnostics Model
**Source:** `~/git/ONT-S508CL-8S`
**Add to modelkit:**
```
TransceiverDiag:
  port: str
  rx_power_dbm: float
  tx_power_dbm: float
  temperature_c: float
  voltage_v: float
  alarm_low: bool
  alarm_high: bool
  module_type: str      # "bidi", "dac", "lr", "sr"
```

### G3. Firmware Credential Tracking
**Source:** ONT projects (AES-OTP, XOR, MD5 type 7)
**Add to observation types:** `credential_scheme: "aes-otp" | "xor-encrypted" | "md5-type7" | "plaintext"`
**Value:** Security posture assessment during verification.

---

## H. Integration Opportunities

### H1. OpenWRT Forum Knowledge Base
**Source:** `~/git/openWRT-Forum-extraction-MCP`
**What:** When Core-Stitcher encounters an OpenWrt device issue, search the forum for solutions.
**Integration:** searchcraft provider adapter or standalone MCP tool call from orchestrator.

### H2. Playwright Browser Automation
**Source:** MCP Gateway (playwright tools available)
**What:** For devices with web-only management (S207CW series), use Playwright to scrape config pages.
**Integration:** switchcraft collector variant that uses browser automation instead of REST API.

### H3. ADB Device Integration
**Source:** `~/git/adb-mcp`
**What:** If Android devices (Samsung A55, H96 TV box) are on the network, collect their state via ADB.
**Integration:** New adapter `vos/androidcraft/` for Android device topology participation.

---

## Priority Matrix

| ID | Module | Effort | Value | Dependencies | Priority |
|----|--------|--------|-------|--------------|----------|
| A1 | Searchcraft | M-L | High | None | **P1** — North Star says backbone needs intelligence |
| B1 | ONTI adapters | S | High | switchcraft exists | **P1** — enables live lab testing |
| C1 | Drift detection | M | High | storekit + git | **P1** — temporal verification |
| D1 | A770 local executor | M | High | executorkit exists | **P1** — private inference |
| E4 | Event persistence | S | Medium | Alembic exists | **P1** — audit trail |
| B3 | Zabbix adapter | M | Medium | MCP gateway ready | **P2** — monitoring correlation |
| C3 | Topology visualizer | L | High | graphkit exists | **P2** — the "show me" feature |
| A3 | Discovery pack | M | Medium | nmap + modelkit | **P2** — semi-auto topology |
| B2 | SFP diagnostics | S | Medium | switchcraft | **P2** — physical layer health |
| C2 | Change planner | L | Very High | verifykit + adapters | **P3** — the write path (big) |
| E1 | Memory model | M | Medium | orchestration | **P3** — cross-run learning |
| E2 | Policy engine | M | Medium | spine | **P3** — safety constraints |
| A2 | Docflow pack | M | Medium | MCP exists | **P3** — docs-as-code |
| C4 | Compliance checker | M | Medium | verifykit | **P3** — security audience |
| D2 | Worktree executor | L | Medium | executorkit | **P4** — code-change automation |
| B4 | WiFi adapter | M-L | Low | AP access needed | **P4** — wireless extension |

---

## Source Traceability

| Source Project | Status | What Core-Stitcher Already Has | What's Left to Harvest |
|---------------|--------|-------------------------------|----------------------|
| VOS-Ruggensgraat | **Merged** | All topology modules | Nothing (fully merged) |
| VOS-Project-Explorer | **Merged** | All agentcore modules | Nothing (fully merged) |
| VOS-Workbench-standalone | **Merged** (spine) | Runtime, config, events, storage | Memory model, policy engine, settings tracing |
| VOS-Network-Failed | **Archived** | Design lessons learned | Oxidized configs, verification scripts, invariants framework |
| VOS-Network-Redux | **Active** | Design principles | Compliance mapping, bypass principle, phase patterns |
| Switchcraft | **Active MCP** | switchcraft adapter | Git-versioned state, drift detection, HIL patterns |
| Searchcraft | **Scaffolded** | Nothing yet | Entire domain pack |
| Homelable | **Active** | Nothing directly | Discovery, health checks, canvas visualization |
| INTELL-A770 | **Spec** | LocalExecutor skeleton | Full implementation |
| Automaker | **Active** | plan→execute→review pattern | Worktree isolation, streaming UI |
| Docflow-MCP | **Working** | Nothing directly | Documentation workflow pack |
| VOS-Docs | **Reference** | North Star adherence | Ongoing architectural discipline |
| ONT-* (3 projects) | **Reference** | Generic switchcraft | Device-specific profiles, SFP diagnostics |
| OG-HomeLab-Net-Orch | **Superseded** | Adapter pattern | Intent-based config, diff/rollback |

---

*This document should be reviewed alongside the authoritative architecture spec at `docs/superpowers/specs/2026-04-07-ruggensgraat-architecture-design.md` and the North Star at `vos-docs/docs/architecture/VOS-NORTH-STAR.md`.*
