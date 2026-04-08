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
- `src/vos_workbench/` — runtime spine (unchanged, do NOT rename)
- `src/vos_workbench/sdk/` — public SDK for modules (the ONLY allowed spine import surface)

### Topology Domain (network-stitcher)
- `src/vos/` — implicit namespace package (NO __init__.py here)
- `src/vos/contractkit/` — module interaction protocols (no logic, no domain objects)
- `src/vos/modelkit/` — domain data types (Device, Port, Link, VLAN, etc.)
- `src/vos/graphkit/` — graph traversal
- `src/vos/storekit/` — topology serialization
- `src/vos/{switchcraft,opnsensecraft,proxmoxcraft}/` — adapter modules
- `src/vos/{collectkit,verifykit,tracekit,interfacekit}/` — engine modules
- `src/vos/apps/preflight/` — preflight workflow app shell
- `src/vos/apps/explorer/` — topology explorer app shell

### AI Orchestrator (project-stitcher)
- `src/vos/agentcore/` — orchestration core
- `src/vos/agentcore/taskkit/` — task models
- `src/vos/agentcore/executorkit/` — executor protocol + implementations (mock, openai, topology, local)
- `src/vos/agentcore/plannerkit/` — work request planning
- `src/vos/agentcore/reviewkit/` — review models + verdicts
- `src/vos/agentcore/storekit/` — run persistence (JSON file store)
- `src/vos/agentcore/orchestration/` — runner, budget policy, feedback loop
- `src/vos/agentcore/registry/` — executor registry
- `src/vos/apps/project_stitcher/` — CLI + HTTP API app shell

## Dependency Rules (HARD)
- `contractkit` → nothing
- Pure libraries (modelkit, graphkit, storekit) → contractkit only
- Runtime modules → pure libraries + contractkit + vos_workbench.sdk.*
- Apps → public module interfaces (contractkit protocols) + spine bootstrap
- `agentcore` → standalone, no spine dependency (uses executorkit protocols)
- NEVER import from vos_workbench.runtime, .storage, .events.bus, etc.
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
