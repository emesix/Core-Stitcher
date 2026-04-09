# Core-Stitcher

## Project
Monorepo backbone: spine runtime + topology domain modules + AI orchestrator.
Stitcher apps are behavior templates loaded onto the backbone.
- **network-stitcher**: topology verification + browsing (preflight + explorer)
- **project-stitcher**: AI orchestration (plan → execute → review → correct)

## Authority
`docs/superpowers/specs/2026-04-07-ruggensgraat-architecture-design.md` is the authoritative architecture spec for the topology domain.

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

## Dependency Rules (HARD)
- `contractkit` → nothing
- Pure libraries (modelkit, graphkit, storekit) → contractkit only
- Runtime modules → pure libraries + contractkit + stitch_workbench.sdk.*
- Apps → public module interfaces (contractkit protocols) + spine bootstrap
- `agentcore` → standalone, no spine dependency (uses executorkit protocols)
- NEVER import from stitch_workbench.runtime, .storage, .events.bus, etc.
- NEVER import between adapter modules (switchcraft must not import opnsensecraft)

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
