# The Stitcher — Three-Part Roadmap

This roadmap is split into three separate concerns with clear boundaries.
Each part gets its own spec, its own exit criteria, and its own implementation cycle.

---

## Part 1: Complete Now — Close the Alpha

**Goal:** Make the homelab genuinely useful through stitch tools. No architecture changes.

**Spec:** `docs/superpowers/specs/2026-04-11-close-alpha-gaps.md`

### What's already done (landed via web Claude Code session)
- `c70c355` — `_maybe_escalate()` wired into runner feedback loop
- `b038ebd` — break early on fail-closed review
- `e4eefd1` — sidecar executor aligned with real A770 API (`/execute` → `/work`)

### What remains

**1a. Gateway resilience**
- File: `src/stitch/contractkit/gateway.py`
- Current: new `httpx.AsyncClient` per call, no retries
- Add: persistent client, configurable retry (3 retries, exponential backoff)
- No circuit breaker yet

**1b. Fix test collection on Python 3.14**
- 72/95 test files fail to collect (`_eval_type()` in Pydantic/typing)
- Only 23 tests runnable — blocks verification
- Likely fix: Pydantic version update or typing-extensions pin

**1c. Verify landed commits**
- Pull latest, run full test suite
- Confirm `_maybe_escalate()` is called (not dead code)
- Confirm sidecar `/work` endpoint works
- Confirm fail-closed breaks early

**1d. Update stale docs/memory**
- Update `project_phase1_progress.md` memory (still says sidecar mismatch, escalation dead)
- Update `alpha-live-results-2026-04-10.md` known issues section

**Exit criteria:**
- Gateway has retries
- All tests collect and pass on Python 3.14
- Landed commits verified working
- Memory/docs reflect current state

**Estimated effort:** 1 week

---

## Part 2: Original Request — Restore the Core Trees

**Goal:** Elevate config, MCP types, and workflows from scattered implementation to interconnected, inspectable backbone objects.

**Spec:** `docs/superpowers/specs/2026-04-11-restore-core-trees.md`

### The problem

The system works but cannot answer:
- What MCP connections exist and which are active?
- Which tools belong to which connection?
- Which agents may use which tools?
- What is the effective merged configuration?

That information is spread across `.mcp.json`, code defaults, env vars, `~/.stitch/secrets.json`, routing policy, and CLAUDE.md prose. ~92% of source files never import from `stitch.core`.

### The trees (ordered by priority)

**Config tree** (first — most scattered, everything else needs it)
```
src/stitch/core/config/
    __init__.py
    models.py    — StitchConfig, GatewayConfig, TopologyConfig, McpServerConfig (< 200 LOC)
    loader.py    — unified loading: env + yaml + defaults (< 150 LOC)
```
Migrate 3 consumers first: `contractkit/gateway.py`, `mcp/engine.py`, `mcp/server.py`

**MCP types tree** (second — highest-traffic contract surface)
```
src/stitch/core/mcp/
    __init__.py
    types.py     — ToolResponse as Pydantic, ErrorCode, DetailLevel (< 150 LOC)
    tools.py     — tool metadata/registration protocol (< 100 LOC)
```
Move from `mcp/schemas.py` → `core/mcp/types.py`. Old file becomes re-export shim.

**Storekit rename** (during MCP work)
- `agentcore/storekit/` → `agentcore/runstore/`
- ~8 internal imports, no external

**Lifecycle documentation** (after config + MCP)
- Do NOT unify — parallel types are intentional
- Add mapping docstring to `core/lifecycle.py`

**Checkpoint gate** — validate Config + MCP adoption before expanding to:

**Workflow tree** (after checkpoint)
```
src/stitch/core/workflow/
    __init__.py
    models.py    — WorkflowStep, WorkflowResult, WorkflowStatus (< 150 LOC)
```

**Event/Run tree** (after workflow)
```
src/stitch/core/events/
    __init__.py
    models.py    — consolidate stream types from core/streams.py
```

**Agent tree + Resource tree** — DEFERRED until a real consumer emerges.

### Constraints
- 200-LOC budget per core file
- Pure data models and protocols — no I/O, no business logic
- Trees define shape; domains fill content
- Do not merge `stitch_workbench` config or `.claude/` settings

**Exit criteria:**
- Effective config inspectable as one object
- MCP types consolidated, schemas.py is a shim
- Core adoption ~7.5% → ~20-25%
- No file in core/ exceeds 200 LOC

**Estimated effort:** 6-8 weeks

---

## Part 3: Future — Domain Expansions

**Goal:** Build project planning, wiki publishing, and resource linking on top of the restored backbone.

**Spec:** `docs/superpowers/specs/2026-04-11-future-domain-expansions.md` (to be written when Part 2 is stable)

### Direction (not yet actionable)

| Phase | What | Depends on |
|---|---|---|
| Rename | The Stitcher (display name only, `stitch.*` stays) | Part 1 done |
| ProjectKit | Project, Goal, Phase, Milestone, Risk, Decision models | Part 2 config tree |
| Project Explorer | Claude Code skill for AI-assisted project dossiers | ProjectKit |
| Wiki publish | One-way: structured data → wiki.js pages | ProjectKit + renderer |
| Resource linking | Projects reference topology devices, run records | ProjectKit + Part 1 |
| UX | Dashboards, timeline, topology canvas | All prior |

### Key decisions already made
- Planning engine = Claude Code skill, NOT a second AI pipeline
- Wiki publish = one-way (structured → rendered), no round-trip editing
- `projectkit` → `core` only (same dep rule as `modelkit` → `contractkit`)
- `WorkRequest` gains `project_id: UUID | None` for linking

### What NOT to do
- No giant config framework
- No forced lifecycle unification
- No domain logic in core trees
- No LLM-driven routing
- No Agent/Resource trees until a consumer emerges

**Detailed planning deferred until Part 2 checkpoint passes.**

---

## Verification (all parts)

After each change:
1. `uv run ruff check src/ tests/`
2. `uv run pytest tests/ -v`
3. `uv run pyright src/`
4. No core file exceeds 200 LOC
5. Migrated modules no longer read env vars directly
