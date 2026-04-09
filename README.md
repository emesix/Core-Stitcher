# Core-Stitcher

Modular agentic backbone for network topology verification and AI-orchestrated infrastructure management.

Core-Stitcher combines a **runtime spine** (module system, config, events, storage), **topology domain modules** (collect, verify, trace, impact-preview), and an **AI orchestrator** (plan, execute, review, correct) into a single monorepo.

## Architecture

```
Layer A ── Agent Backbone (project-stitcher)
           plan -> execute -> review -> correct
           |
Layer B ── Topology Domain (network-stitcher)
           collect -> merge -> verify -> trace -> impact
           |
Layer C ── Executors
           Claude | OpenAI | Local LLM (A770)
```

### Spine (`stitch_workbench`)

Runtime framework: module registry via entry points, topological startup ordering, typed YAML config with Pydantic validation, async event bus, SQLModel persistence, FastAPI endpoints.

### Topology Domain (`stitch.*`)

| Module | Type | Purpose |
|---|---|---|
| **contractkit** | protocols | CollectorProtocol, VerifierProtocol, TracerProtocol, etc. |
| **modelkit** | data types | Device, Port, Link, VLAN, Observation, VerificationReport |
| **graphkit** | pure library | BFS, neighbors, vlan_ports, diagnostics, subgraph |
| **storekit** | serialization | load/save topology JSON (schema versioned) |
| **switchcraft** | adapter | Collect from network switches via MCP gateway |
| **opnsensecraft** | adapter | Collect from OPNsense firewalls via MCP gateway |
| **proxmoxcraft** | adapter | Collect from Proxmox hypervisors via MCP gateway |
| **collectkit** | engine | Merge observations from all adapters, detect conflicts |
| **verifykit** | engine | Compare declared vs observed topology, produce reports |
| **tracekit** | engine | VLAN path tracing + change impact preview |
| **interfacekit** | integration | HTTP API + MCP tool exposure |

### AI Orchestrator (`stitch.agentcore`)

| Module | Purpose |
|---|---|
| **taskkit** | Task records, status, priority, outcomes |
| **plannerkit** | Deterministic work decomposition (no LLM needed) |
| **executorkit** | Protocol + implementations (Mock, OpenAI, Local, Topology) |
| **reviewkit** | Review models, verdicts, severity-aware findings |
| **orchestration** | RunOrchestrator with budget policies and feedback loops |
| **registry** | Domain-aware executor selection with health filtering |
| **storekit** | Run persistence (JSON file store) |

### Apps

- **preflight** -- topology verification workflow (collect -> merge -> verify)
- **explorer** -- read-only topology browser (neighbors, VLAN map, trace, impact)
- **project-stitcher** -- CLI + HTTP API for AI-orchestrated task execution

## Quick Start

```bash
# Install
uv sync

# Run checks
uv run ruff check src/ tests/
uv run pytest tests/ -v
uv run pyright src/

# Lab preflight (requires MCP gateway at localhost:4444)
uv run python scripts/lab_preflight.py --health-only
uv run python scripts/lab_preflight.py --output output/run1

# CLI
uv run project-stitcher "Verify network topology" --domain topology
```

## Requirements

- Python 3.14+
- MCP gateway with switchcraft, opnsense, and proxmox servers (for live collection)
- `MCP_GATEWAY_AUTH` env var for gateway authentication

## Development

```bash
uv run ruff check src/ tests/     # Lint
uv run ruff format src/ tests/    # Format
uv run pytest tests/ -v           # Test (646 tests)
uv run pyright src/               # Type check
```

## Dependency Rules

Hard constraints enforced across the codebase:

- `contractkit` imports nothing
- Pure libraries (modelkit, graphkit, storekit) import contractkit only
- Adapters never import each other
- Apps resolve modules via contractkit protocols, not direct imports
- `agentcore` is standalone -- no spine dependency

## Project Status

**Alpha** -- architecture frozen, topology read path complete, AI orchestrator functional.

Active work: live hardware integration, drift detection, first write operation (VLAN apply via Switchcraft MCP).

See [docs/INTEGRATION-PLAN-GROUNDED.md](docs/INTEGRATION-PLAN-GROUNDED.md) for the roadmap.

## License

Private -- all rights reserved.
