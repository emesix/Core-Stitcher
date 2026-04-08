# Explorer Alpha Roadmap

*Post-foundation roadmap. Goal: turn the prototype into a restart-safe,
queryable, testable, documented alpha runtime.*

**Exit criteria:** DB-backed events persist across restart, health/readiness
are distinct, module failures are surfaced, event queries are paginated,
boot sequence is test-covered, docs describe actual runtime contracts.

---

## Phase 1 — Stabilize contracts (next session)

These items harden what exists. No new features.

### 1.1 Schema migrations

- Replace `create_tables()` with Alembic migration framework
- Create initial migration from current SQLModel tables
- Verify migration runs on empty DB and is idempotent
- **Why first:** Without this, any schema change breaks existing DBs

### 1.2 Health endpoint split

- `GET /api/v1/livez` → process alive (always 200)
- `GET /api/v1/readyz` → startup complete, deps healthy (503 if not)
- `GET /api/v1/health` → rich diagnostic payload (current behavior)
- **Why:** Conflating liveness and readiness causes silent failures

### 1.3 `/events` pagination and filtering

- Add `?offset=`, `?limit=`, `?since=` (ISO timestamp)
- Add `?source=` filter (glob pattern)
- Add `?severity=` filter
- Enforce max page size (1000)
- Return stable ordering (time ASC, id for tiebreaker)
- **Why:** Without pagination, `/events` is a debugging toy, not a platform API

### 1.4 Contract tests

Tests that verify the structural promises, not just happy paths:

- Boot persists a `system.loaded` event to SQLite
- Overflow emits `bus.subscriber.overflow` and marks subscriber degraded
- `/health` reflects failed modules from startup plan
- `/events` returns DB-backed records after restart (new process, same DB)
- DB unavailable at boot fails with clear error
- Partial module startup is reflected in health

---

## Phase 2 — Projection layer

Derived views from raw events and runtime state.

### 2.1 System status projection

- `GET /api/v1/system` → overall system health, uptime, boot time,
  active/failed/degraded module counts

### 2.2 Module status projection

- `GET /api/v1/modules/{uuid}/status` → runtime state, last health check,
  startup group, dependency satisfaction

### 2.3 Subscriber status

- `GET /api/v1/bus/subscribers` → list subscribers with degraded flag,
  overflow count, queue depth

### 2.4 Recent failures

- `GET /api/v1/failures` → last N critical events, failed modules,
  overflow incidents

---

## Phase 3 — First real module types

Turn the module registry from "can discover types" into "can run types."

### 3.1 Module lifecycle manager

- `start(module_uuid)` → instantiate type, call `start()`, update health
- `stop(module_uuid)` → call `stop()`, update health
- `POST /api/v1/modules/{uuid}/start`
- `POST /api/v1/modules/{uuid}/stop`
- Restart policy enforcement (3 restarts with backoff)

### 3.2 `exec.shell` module type

- First real module: runs shell commands
- Config: `cwd`, `allowed_commands`, `timeout`
- Capabilities: `shell.execute`
- Events: `command.started`, `command.completed`, `command.failed`

### 3.3 `core.router` module type (stub)

- Wraps the agent loop pattern (borrowed from Claude Code research)
- Config: `model`, `system_prompt`, `max_turns`, `budget`
- For alpha: stub that accepts a prompt and returns "not implemented"
- Proves the module lifecycle works with a core module

---

## Phase 4 — Docs and SSOT

### 4.1 Architecture docs tree

- `docs/contracts/event-model.md` — event types, envelope schema
- `docs/contracts/health-model.md` — liveness/readiness/health semantics
- `docs/contracts/module-lifecycle.md` — states, transitions, restart
- `docs/contracts/api-reference.md` — generated from FastAPI OpenAPI

### 4.2 Generated docs

- Module inventory from registry
- Event type catalog from code
- Health schema from Pydantic models
- Startup sequence from DAG

---

## Priority for tomorrow

Focus on **Phase 1 only**. Four items:

1. Alembic migrations
2. livez/readyz/health split
3. /events pagination
4. Contract tests

That's one session of focused work with pre-planned tasks.

---

## What to defer

- WebSocket event streaming
- Multi-project support
- Real module lifecycle (start/stop)
- TUI client
- Agent orchestration
- Provider routing

These are all real but none of them should happen before Phase 1 is solid.

---

*This roadmap should be reviewed with ChatGPT before execution.*
