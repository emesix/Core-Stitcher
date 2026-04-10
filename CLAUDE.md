# Core-Stitcher

## Project
Monorepo backbone: spine runtime + topology domain modules + AI orchestrator.
Stitcher apps are behavior templates loaded onto the backbone.
- **network-stitcher**: topology verification + browsing (preflight + explorer)
- **project-stitcher**: AI orchestration (plan → execute → review → correct)

## Authority
- `docs/superpowers/specs/2026-04-07-ruggensgraat-architecture-design.md` — topology domain architecture
- `docs/superpowers/specs/2026-04-10-stitch-mcp-server-design.md` — MCP server (9+3 tools)
- `docs/specs/2026-04-10-core-stitcher-planning-after-claude-code-ga.md` — strategic direction

## Commands
- **Lint:** `uv run ruff check src/ tests/`
- **Format:** `uv run ruff format src/ tests/`
- **Test:** `uv run pytest tests/ -v`
- **Type check:** `uv run pyright src/`
- **All checks:** `uv run ruff check src/ tests/ && uv run pytest tests/ -v && uv run pyright src/`

## Conventions
- Python 3.14, async-first
- Pydantic v2 for all data models
- FastAPI for API layer
- SQLModel for database models (spine only)
- structlog for logging
- YAML for config, Pydantic for validation
- ruff for lint+format, pytest with pytest-asyncio, TDD

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
- `src/stitch/agentcore/executorkit/` — executor protocol + implementations (mock, openai, topology, local)
- `src/stitch/agentcore/plannerkit/` — work request planning
- `src/stitch/agentcore/reviewkit/` — review models + verdicts
- `src/stitch/agentcore/storekit/` — run persistence (JSON file store)
- `src/stitch/agentcore/orchestration/` — runner, budget policy, feedback loop
- `src/stitch/agentcore/registry/` — executor registry
- `src/stitch/apps/project_stitcher/` — CLI + HTTP API app shell

### Operator Layer
- `src/stitch/core/` — shared types (Resource, Command, Query, Filter, Stream, Lifecycle, errors)
- `src/stitch/sdk/` — API client, stream client, config/auth
- `src/stitch/mcp/` — MCP server (12 tools: topology, trace, impact, preflight, interface, snapshots)
- `src/stitch/mcp/tools/` — thin tool wrappers (FastMCP decorators)
- `src/stitch/mcp/services/` — use-case orchestration (preflight, topology, interface, snapshot)
- `src/stitch/apps/operator/` — CLI (Typer, 11 command groups)
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

## Git
- Check status before changes
- Suggest commits at logical points
- Never push without asking
- Never commit secrets
