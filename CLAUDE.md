# Core-Stitcher

## Project
Monorepo backbone: spine runtime + topology domain modules + AI orchestrator.
Stitcher apps are behavior templates loaded onto the backbone.
- **network-stitcher**: topology verification + browsing (preflight + explorer)
- **project-stitcher**: AI orchestration (plan → execute → review → correct)

## Authority
- `docs/superpowers/specs/2026-04-07-ruggensgraat-architecture-design.md` — topology domain architecture
- `docs/superpowers/specs/2026-04-10-stitch-mcp-server-design.md` — MCP server (12 tools)
- `docs/superpowers/specs/2026-04-10-alpha-executor-routing-design.md` — executor routing + backends
- `docs/superpowers/specs/2026-04-10-strategic-direction-reassessment.md` — strategic direction (supersedes planning doc)

Authority order:
1. Explicit user instruction in the current session
2. Specs and runbooks listed in Authority
3. CLAUDE.md
4. Incidental docs/comments

If code appears to diverge from an authoritative spec, do not assume the divergence is intentional. Check tests, recent commits, and adjacent runbooks/specs before changing behavior.

## Start Here

For a safe default session:
1. Read the Authority docs listed above
2. Run unit validation: `uv run ruff check src/ tests/ && uv run pytest tests/ -v -m "not integration" && uv run pyright src/`
3. For read-only live validation, use:
   - `scripts/alpha_run.py` for executor routing / alpha checks
   - MCP topology, trace, diagnostics, impact tools for topology inspection
   - MCP snapshot tools for OPNsense state inspection (queries live APIs)
4. Do not run write-path operations unless the user explicitly asks and is present

README is for human project overview. For operator behavior and implementation decisions, follow Authority docs and this CLAUDE.md.

## Commands
- **Lint:** `uv run ruff check src/ tests/`
- **Format:** `uv run ruff format src/ tests/`
- **Test (unit):** `uv run pytest tests/ -v -m "not integration"`
- **Test (live/integration):** `uv run pytest tests/ -v -m integration`
- **Test (all):** `uv run pytest tests/ -v` — only when intentionally running both unit and integration
- **Type check:** `uv run pyright src/`
- **All checks:** `uv run ruff check src/ tests/ && uv run pytest tests/ -v -m "not integration" && uv run pyright src/`

## Tool Safety Classes
- **Pure local (no network):** topology_summary, devices, device_detail, device_neighbors, diagnostics, trace_vlan, impact_preview, snapshot_list, snapshot_diff
- **Live read-only (queries OPNsense/adapters):** snapshot_capture, preflight_run — safe but hits real APIs; mind OPNsense rate limits
- **Write-path (changes state):** interface_assign with `dry_run=false` — hook-guarded, requires explicit user approval
- **Manual approval required:** any operation that changes live network or firewall state

## Operational Safety
- Pre-tool-use hook blocks `stitch_interface_assign dry_run=false` unless explicitly confirmed
- Post-tool-use hook logs all write-path calls to `~/.stitch/audit.jsonl`
- Stop hook reminds about unapplied changes
- `.mcp.json` passes SSH credentials to the MCP server — stitch tools can SSH to OPNsense
- Do NOT treat the sidecar as a general compute endpoint — it is intentionally thin (alpha only)
- Integration tests (`@pytest.mark.integration`) hit live backends and may burn API credits

## Conventions
- Python 3.14, async-first
- Pydantic v2 for all data models
- FastAPI for API layer
- SQLModel for database models (spine only)
- structlog for logging
- ruff for lint+format, pytest with pytest-asyncio
- API keys: env var checked first, then `~/.stitch/secrets.json` (key map in `openai_compat.py`)

## Code Style
- Line length: 100
- Type annotations on public functions
- No docstrings on obvious functions
- Prefer composition over inheritance
- Small focused files

## Package Structure
### Spine
- `src/stitch_workbench/` — runtime spine
- `src/stitch_workbench/sdk/` — public SDK for modules (the ONLY allowed spine import surface)

### Topology Domain (network-stitcher)
- `src/stitch/` — implicit namespace package (NO __init__.py here)
- `src/stitch/contractkit/` — module interaction protocols (no logic, no domain objects)
- `src/stitch/modelkit/` — domain data types (Device, Port, Link, VLAN, etc.)
- `src/stitch/graphkit/` — graph traversal
- `src/stitch/storekit/` — topology serialization
- `src/stitch/{switchcraft,opnsensecraft,proxmoxcraft}/` — adapter modules
- `src/stitch/{collectkit,verifykit,tracekit,interfacekit}/` — engine modules
- `src/stitch/apps/preflight/` — preflight workflow app shell
- `src/stitch/apps/explorer/` — topology explorer app shell

### AI Orchestrator (project-stitcher)
- `src/stitch/agentcore/` — orchestration core
- `src/stitch/agentcore/taskkit/` — task models
- `src/stitch/agentcore/executorkit/` — executor protocol + implementations (mock, openai_compat, topology, local, sidecar)
- `src/stitch/agentcore/plannerkit/` — work request planning
- `src/stitch/agentcore/reviewkit/` — review models + verdicts
- `src/stitch/agentcore/storekit/` — run persistence (JSON file store)
- `src/stitch/agentcore/orchestration/` — runner, budget policy, routing policy, feedback loop
- `src/stitch/agentcore/registry/` — executor registry
- `src/stitch/apps/project_stitcher/` — CLI + HTTP API app shell

### Operator Layer
- `src/stitch/core/` — shared types (Resource, Command, Query, Filter, Stream, Lifecycle, errors)
- `src/stitch/sdk/` — API client, stream client, config/auth
- `src/stitch/mcp/` — MCP server (12 tools: topology, trace, impact, preflight, interface, snapshots)
- `src/stitch/mcp/tools/` — thin tool wrappers (FastMCP decorators)
- `src/stitch/mcp/services/` — use-case orchestration (preflight, topology, interface, snapshot)
- `src/stitch/apps/operator/` — CLI (Typer)
- `src/stitch/apps/tui/` — Terminal UI (Textual, 3-zone layout)
- `src/stitch/apps/lite/` — Minimal HTML UI (FastAPI + Jinja2)
- `frontend/` — React WebUI (TypeScript, TanStack Router/Query)
- `frontend/src-tauri/` — Desktop wrapper (Tauri v2)

### Claude Code Extensions
- `.mcp.json` — project-scoped MCP server config (stitch stdio server)
- `.claude/settings.json` — hooks registration
- `.claude/hooks/` — pre-tool-use safety, post-tool-use audit, stop session check
- `.claude/skills/` — network-operator, topology-verifier, remediation-planner, network-diagnostician
- `.claude/agents/` — topology-triage (read-only specialist)

## Executor Backends
Four alpha backends, two categories:

**Inference (chat completions):** `local-gpu`, `local-cpu`, `openrouter`
**Compute (structured work):** `local-sidecar`

- `base_url` is bare origin only (never include path). `api_path` and `models_path` are separate fields.
- When `models_path=None`, health uses TCP connect (avoids burning inference tokens on OVMS).
- Sidecar implements `ExecutorProtocol` only (no review). It is not a distributed job framework.
- Backend addresses and model IDs are in `executorkit/local.py` defaults and `alpha_routing_policy()`.

## Dependency Rules (HARD)
- `contractkit` → nothing
- Pure libraries (modelkit, graphkit, storekit) → contractkit only
- Runtime modules → pure libraries + contractkit + stitch_workbench.sdk.*
- Apps → public module interfaces (contractkit protocols) + spine bootstrap
- `agentcore` → standalone, no spine dependency (uses executorkit protocols)
- NEVER import from stitch_workbench.runtime, .storage, .events.bus, etc.
- NEVER import between adapter modules (switchcraft must not import opnsensecraft)
- `stitch.mcp` → domain packages (modelkit, storekit, verifykit, etc.) + contractkit gateway
- `stitch.mcp` must NOT import from client packages (operator CLI, tui, lite, web)
- Client packages must NOT import from `stitch.mcp`

## Architecture Rules
- Service-primary interaction; events for audit/telemetry only
- verifykit and tracekit are pure evaluators with explicit inputs
- interfacekit resolves PreflightWorkflowProtocol, never low-level modules
- Module config is typed and validated before module code sees it
- One ModuleType can have multiple instances
- Routing is deterministic and config-driven — never LLM-driven
- Routing precedence: tag-based rules > step-kind rules > global default
- Fallback = same capability, different instance (availability). Escalation = quality problem, stronger model.
- `fail_closed=True` means stop — do not silently substitute a different executor
- Tags (`high_risk`, `write_path`) on WorkRequest/PlannedTask force routing to external with fail-closed
