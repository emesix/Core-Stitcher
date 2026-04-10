# The Stitcher — Strategic Roadmap

## Context

Core-Stitcher has proven its domain engine tonight: 949 tests, alpha routing with 4 backends, live OPNsense management rebuild, 4 switches online. The orchestration loop (plan→execute→summarize→review→correct) works end-to-end with real inference.

The question is: what comes next? The answer from both the user's vision and the ChatGPT architectural analysis is: **don't build more network features — build the platform skeleton that makes every future domain (topology, project planning, wiki/knowledge) plug in the same way.**

The core insight is that structural pillars are missing from the backbone. The runtime, orchestration, and routing are solid. But the **tree-ness** — interconnected, inspectable, policy-aware configuration — is lost. What exists works, but it's flat and scattered instead of being a unified graph you can query and reason about.

---

## What was lost: the unified structure

The system can do MCP, routing, config, and agents. But it cannot cleanly answer:

- What MCP connections exist? Which are active?
- Which tools belong to which connection?
- Which workflows depend on which connections?
- Which agents may use which tools?
- Which secrets source is active for this connection?
- Which tools are read-only vs write-path?
- Which profile is currently loaded?
- What is the effective merged configuration?

That information exists — spread across `.mcp.json`, code defaults, env vars, `~/.stitch/secrets.json`, routing policy, CLAUDE.md prose, and implicit knowledge. But it's not a single inspectable tree.

The original vision was: **MCP connections, configs, agents, workflows, and tools are real backbone objects with graph relationships between them**, not scattered implementation details.

---

## The 6 Core Trees — as a connected graph

These are not flat model files. They are **interconnected nodes** where you can trace relationships:

```
Config Tree                    MCP Tree                     Agent Tree
┌─────────────┐           ┌──────────────────┐          ┌─────────────────┐
│ Profile      │──loads──→│ MCP Connection    │←─uses────│ Agent           │
│  ├ lab       │           │  ├ identity      │           │  ├ capabilities │
│  ├ production│           │  ├ target/url    │           │  ├ allowed tools│
│  └ offline   │           │  ├ auth source   │──refs──→ │  ├ allowed MCP  │
├─────────────┤           │  ├ health/status  │          │  └ policy       │
│ Environment  │           │  ├ safety class  │          └─────────────────┘
│  ├ defaults  │           │  └ capabilities  │                │
│  ├ overrides │           ├──────────────────┤                │
│  └ secrets   │──refs──→ │ Tool             │←─binds─────────┘
└─────────────┘           │  ├ schema        │
                           │  ├ safety class  │          Workflow Tree
                           │  ├ read/write    │          ┌─────────────────┐
                           │  ├ MCP connection│←─uses────│ Workflow         │
                           │  └ audit class   │           │  ├ steps        │
                           └──────────────────┘           │  ├ dependencies │
                                                          │  ├ allowed MCP  │
Event/Run Tree             Resource Tree                  │  ├ approvals    │
┌─────────────┐           ┌──────────────────┐           │  └ review loops │
│ Run          │──about──→│ Resource          │←─acts on──└─────────────────┘
│  ├ steps     │           │  ├ devices       │
│  ├ decisions │           │  ├ projects      │
│  ├ audit     │           │  ├ docs          │
│  └ outcomes  │           │  └ runs          │
└─────────────┘           └──────────────────┘
```

### What each tree IS

| Tree | What it answers | What a node looks like | Key relationships |
|---|---|---|---|
| **Config tree** | How the system is configured | Profile → environment → overrides → secrets refs → effective config | Profiles load MCP connections, activate tools, set policies |
| **MCP tree** | What connections and tools exist | Connection → target + auth + health + safety + capabilities → tools | Tools hang off connections. Workflows bind to connections. Agents get permission to connections. |
| **Workflow tree** | How work is structured | Workflow → steps → dependencies → approvals → review loops → allowed MCP bindings | Workflows declare which MCP connections they need. A preflight workflow needs topology tools. A publish workflow needs wiki tools. |
| **Agent tree** | Who can do what | Agent → capabilities → allowed tools → allowed workflows → policy constraints | Agents see specific tools, not all tools. An agent allowed `topology` tools cannot call `write_path` tools unless explicitly granted. |
| **Resource tree** | What exists | Resource → URI + type + status + parent + children | Devices, projects, docs, runs are all resources with `stitch:/` URIs |
| **Event/Run tree** | What happened | Run → steps → decisions → audit entries → outcomes | Every step traces back to which MCP connection, which agent, which workflow |

### What currently exists vs what's missing

| Tree | Functionality exists | Structure exists | Graph relationships exist |
|---|---|---|---|
| Config | Partially (scattered files) | No | No |
| MCP | Yes (gateway + .mcp.json) | No (wrappers, not objects) | No |
| Workflow | Yes (agentcore orchestration) | Partially (locked in agentcore) | No |
| Agent | Yes (ExecutorRegistry + routing) | Partially | No |
| Resource | Seeds (`core/resources.py`) | Partially | No |
| Event/Run | Yes (RunRecord + audit.jsonl) | Partially (split across modules) | No |

**The functionality is there. The unified inspectable structure is not.**

---

## What already exists in `stitch/core/`

The core package has seeds of several trees:
- `resources.py` — `ResourceURI` with `stitch:/{type}/{id}` scheme, `Resource` summary type
- `commands.py` — `Command` with `RiskLevel`, `CommandSource`, `ExecutionMode`
- `lifecycle.py` — `LifecycleState` with valid transitions
- `queries.py` — `Filter`, `Query`, `QueryResult`
- `streams.py` — `StreamEvent`, `StreamTopic`
- `auth.py` — `Capability`, `Session`
- `errors.py` — error hierarchy

These are good building blocks. The gap is that they're not yet **connected into trees** that the rest of the system uses as organizing structures.

---

## Three Stages

The roadmap follows one principle: **make it work → make the backbone right → make the expansions.**

- **Stage A (Utility):** Finish alpha, make the homelab genuinely useful
- **Stage B (Architecture):** Restore the core trees — config, workflows/agents, MCP/tools
- **Stage C (Value):** Build project planning, wiki publishing, structured knowledge

If you do add-ons first, you build on a half-restored skeleton and create more cleanup later. If you fix the backbone first without finishing alpha, you polish architecture while the homelab still lacks practical value. So: enough alpha to become useful, then backbone correction, then domain growth.

---

## Proposed Roadmap (8 phases)

### Phase 1 — Finish the alpha, make it useful [Stage A: Utility]

**What:** Close every live gap. Make the homelab genuinely useful through the stitch tools before touching architecture.

Concrete items:
- Fix sidecar executor API mismatch (`/execute` → `/work`, health reads `details` not `stage`)
- Wire `_maybe_escalate()` into runner feedback loop (currently dead code — escalation triggers on review rules are metadata only)
- Break early on fail-closed in review loop (3 pointless SKIPPED steps)
- Wire alpha bootstrap into project_stitcher app (replace MockExecutor with real backends)
- Update `topologies/lab.json` to reflect rebuilt network (4 switches, new IPs, bridge)
- Run preflight against live topology with real switch data
- Prove the full read-only loop with real topology data (not MockExecutor)

**Exit criteria:**
- GPU inference path solid with real topology
- CPU fallback behavior understood and correctly bounded
- Sidecar fixed and proven with live `/work` endpoint
- Escalation actually fires (not just exists as dead code)
- Real topology data used end-to-end
- Alpha is genuinely trustworthy before any write-path expansion

### Phase 1.5 — Restore the core trees [Stage B: Architecture]

**What:** Elevate the 6 structural trees from scattered implementation details to interconnected, inspectable backbone objects. This is not "add model files" — it's restoring the graph relationships that make the system queryable.

**Why before domains:** Without this, every new domain invents its own config loading, its own workflow shape, its own tool registration. The trees are what prevent that. They are the organizing skeleton.

**The key restoration: MCP connections as first-class objects.**

An MCP connection should be a real node, not a `.mcp.json` entry plus code defaults plus env vars:

```python
class McpConnection(BaseModel):
    """A first-class MCP connection in the backbone."""
    id: str                              # "stitch-local", "opnsense-gw", "wikijs"
    target: str                          # "http://localhost:4444/mcp/"
    auth: AuthRef | None = None          # pointer to secrets tree
    health: HealthStatus = HealthStatus.UNKNOWN
    safety_class: SafetyClass = SafetyClass.READ_ONLY
    capabilities: list[str] = []         # ["topology", "firewall", "wiki"]
    tools: list[str] = []                # tool IDs registered on this connection
    allowed_agents: list[str] = []       # which agents may use this connection
    allowed_workflows: list[str] = []    # which workflows may bind to this
    profile: str = "default"             # which config profile activates this
```

Then you can answer: "which MCP connections does the preflight workflow use?" or "which agents can call write-path tools?" by querying the tree, not by reading prose in CLAUDE.md.

**Proposed core layout:**

```
src/stitch/core/
    resources.py      — exists: expand with type registry
    config/
        __init__.py
        profiles.py   — Profile, Environment, effective config resolution
        secrets.py    — SecretRef (pointer, never value), resolution strategy
    connections/
        __init__.py
        mcp.py        — McpConnection, McpTool, SafetyClass, HealthStatus
        registry.py   — ConnectionRegistry (inspectable, queryable)
    workflows/
        __init__.py
        models.py     — Workflow, Step, Dependency, Approval, ReviewLoop
        bindings.py   — WorkflowMcpBinding (which connections a workflow needs)
    agents/
        __init__.py
        models.py     — Agent, Capability, ToolAccess, PolicyConstraint
        permissions.py — what an agent may do (tool-level, connection-level)
    runs/
        __init__.py
        models.py     — Run, StepRecord, AuditEntry, Outcome (unified)
    # existing files stay:
    commands.py, lifecycle.py, queries.py, streams.py, auth.py, errors.py
```

**Config tree with profiles and environment switching:**

```python
class Profile(BaseModel):
    """A named configuration profile that activates specific connections, policies, and tools."""
    name: str                            # "lab", "production", "offline", "local-only"
    connections: list[str] = []          # which MCP connection IDs are active
    routing_policy: str = "default"      # which routing policy to load
    safety_overrides: dict[str, SafetyClass] = {}
    secrets_source: str = "~/.stitch/secrets.json"

class EffectiveConfig(BaseModel):
    """The fully resolved config — defaults + profile + env overrides + session overrides."""
    active_profile: str
    active_connections: list[McpConnection]
    active_routing: RoutingPolicy
    active_agents: list[Agent]
    resolved_secrets: dict[str, str]     # key→source (never values in this model)
```

This lets you answer "what is the effective merged config right now?" with one object.

**Relationship to existing code:**

| Current code | Becomes | In tree |
|---|---|---|
| `.mcp.json` | Serialization of McpConnection nodes | MCP tree |
| `OpenAIExecutorConfig` defaults | Connection config under a profile | Config tree |
| `RoutingPolicy` in `routing.py` | Referenced by profile, bound to workflows | Config + Workflow tree |
| `ExecutorRegistry` | Implementation of Agent tree's capability matching | Agent tree |
| `~/.stitch/secrets.json` | SecretRef targets, resolved by config tree | Config tree |
| `CLAUDE.md` Tool Safety Classes | `SafetyClass` on McpTool and McpConnection | MCP tree |
| `pre-tool-use-safety.sh` hook | Policy enforcement reading from Agent/Tool tree | Agent + MCP tree |
| `audit.jsonl` | AuditEntry in Run tree | Event tree |

**Critical constraints:**
- Trees are pure data models and protocols. No I/O, no business logic.
- Domain packs attach to trees; core defines the shape.
- agentcore's orchestration becomes an *implementation* of the workflow tree, not the definition.
- FastMCP stays as the wire protocol. The MCP tree handles discovery, classification, and policy — not transport.
- Each subpackage stays small. If any file exceeds ~200 lines, it's doing too much.

**Risk:** Over-engineering. The trees must be small, boring, and explicit. They are not a framework — they are a data model with relationships.

### Phase 2 — Rename to The Stitcher [Stage B: Architecture]

**What:** Display-name only. Python package stays `stitch`. Entry points stay `stitch`, `stitch-mcp`, etc.

Changes:
- `pyproject.toml` project name → `the-stitcher`
- README, docs, CLAUDE.md references
- MCP server display name
- Git repo name (GitHub rename)

**NOT changed:** Import paths, package structure, test files, CLI commands.

**When:** After Phase 1.5 is stable. The rename signals "this is a platform now" not "this is a network tool."

**Exit criteria:**
- Effective config is inspectable as one object
- Workflows and agents are first-class, not scattered conventions
- MCP/tool registry is explicit with safety class, connection binding, agent permissions
- Domains plug in cleanly without core churn
- Backbone feels boring and trustworthy

### Phase 3 — Add project-planning domain model (projectkit) [Stage C: Value]

**What:** Structured planning objects following the existing kit pattern.

```
src/stitch/projectkit/
    __init__.py
    models.py       — Project, Goal, Phase, Milestone, Risk, Decision, Estimate
    store.py         — ProjectStore protocol + JsonProjectStore
    queries.py       — filter/search/aggregate projects
    renderer.py      — render Project → structured markdown (for wiki publish)
```

**Models attach to core trees:**
- Resource tree: Projects, Phases, Risks are resources with `stitch:/project/{id}` URIs
- Workflow tree: scope generation, estimation, review are workflow instances
- Tool tree: planning MCP tools register in the tool registry
- Event tree: planning runs and revisions tracked as run events

**Integration with agentcore:**
- `WorkRequest` gains `project_id: UUID | None = None` (backward-compatible)
- `RunRecord` carries project link via `request.project_id`
- `JsonRunStore.list_runs()` gains optional `project_id` filter

**Dependency rules:** `projectkit` → `core` only (same as modelkit → contractkit). Never depends on agentcore, modelkit, or adapters. Reference IDs (UUIDs, strings) link to other domains — not imported types.

### Phase 4 — Project Explorer as planning engine [Stage C: Value]

**What:** AI-assisted project dossier generation. Take a vague idea → produce structured Project with goals, phases, estimates, risks, decisions, open questions.

**Critical design decision:** This is a **Claude Code skill**, not a second AI pipeline. Claude Code is already the primary operator. The planning engine is:
1. A Claude Code skill (`/project-new`, `/project-review`)
2. That calls projectkit MCP tools to create/query/update project objects
3. Using agentcore orchestration for AI-assisted estimation/review if needed

**NOT building:** A separate AI planner that duplicates what Claude Code already does.

**First version:** Read-only, human-reviewed:
- Propose project structure from description
- Ask targeted questions about gaps
- Generate estimate ranges with explicit uncertainty
- Highlight risks and assumptions
- Revise on feedback

### Phase 5 — Publish to wiki/SSOT [Stage C: Value]

**What:** One-way publish from structured projectkit data to wiki.js pages.

**Architecture:**
- `projectkit/renderer.py` — pure function: `Project → markdown` (no I/O, testable)
- `mcp/services/wiki_service.py` — calls wiki.js MCP gateway tools (same pattern as SnapshotService)
- `mcp/tools/publish.py` — `stitch_publish_project` MCP tool

**Wiki page structure:**
```
/projects/{name}/overview     — main project page
/projects/{name}/decisions    — decision log  
/projects/{name}/risks        — risk register
/projects/{name}/phases/{n}   — per-phase detail
```

**One-way only:** Structured data → wiki output. Wiki is generated, never read back to reconstruct state. Round-trip editing deferred.

**Uses existing wiki.js gateway tools:** create-page, update-page, get-page, search, get-tags — all already available.

### Phase 6 — Connect projects to real resources [Stage C: Value]

**What:** Link project objects to topology devices, run records, and infrastructure facts.

- Project model gains reference fields: `topology_path`, `run_ids`, `device_ids`
- Project wiki page can embed live topology facts
- Project risk can reference a real topology weakness
- Project phase can depend on a network migration

**This is where The Stitcher becomes more than a planner or a network tool** — it ties plans to reality.

### Phase 7 — Make it pleasant to use [Stage C: Value]

**What:** UX improvements after the model and publishing are right.
- Project timeline views
- Cost/risk dashboards
- Decision logs with history
- "Show me what changed since last review"
- Better wiki templates
- Topology canvas (the one custom UI Claude Code can't replace)

---

## Dependency order

```
Phase 1 (close alpha gaps)
    │
    v
Phase 1.5 (core trees) ──────────── can overlap with Phase 1 tail
    │
    ├──> Phase 2 (rename) ────────── independent, can overlap with 1.5 or 3
    │
    v
Phase 3 (projectkit models)
    │
    ├──> Phase 4 (planning engine) ─ requires Phase 3
    │
    ├──> Phase 5 (wiki publish) ──── requires Phase 3, can overlap with 4
    │
    v
Phase 6 (connect resources) ─────── requires Phase 3 + Phase 1
    │
    v
Phase 7 (UX) ────────────────────── ongoing tail
```

**Strictly sequential:** 1 → 1.5 → 3 → (4,5,6) → 7
**Can overlap:** 2 with anything. 4 and 5 in parallel. 1.5 tail with Phase 1.

---

## Top 3 risks

### 1. Core trees become over-engineered
The trees must be small, boring, and explicit. If `core/config.py` tries to be a full configuration framework, it will collapse under its own weight. Each tree should be 100-200 lines of Pydantic models and protocols. No generic DSLs.

**Mitigation:** Size budget per file. If it grows past 200 lines, it's doing too much.

### 2. Phase 4 scope creep
"AI-assisted project dossier generation" is vague enough to expand forever. The risk is building a complex AI pipeline when Claude Code + MCP tools is sufficient.

**Mitigation:** Phase 4 is a Claude Code skill that calls projectkit MCP tools. The AI is Claude Code itself. No second orchestration pipeline.

### 3. Storekit naming collision
Three unrelated things called "store": topology storekit, agentcore storekit, and future projectkit store. Developer confusion is real.

**Mitigation:** Before Phase 3, rename `agentcore/storekit/` → `agentcore/runstore/`. Topology storekit stays. Projectkit uses `projectkit/store.py` (single file, not subpackage).

---

## What NOT to do

- No giant generic "document management system"
- No replacing NetBox/Ralph/wiki/git all at once
- No freeform AI planner with no structured project model
- No full round-trip wiki editing from day one
- No big rename before alpha hardening finishes
- No domain logic in core trees (core defines shape, domains fill it)
- No LLM-driven routing (stays deterministic, config-driven)

---

## Summary

**Make it work → make the backbone right → make the expansions.**

| Stage | Phases | Exit gate |
|---|---|---|
| **A: Utility** | 1 (alpha hardening) | Homelab is genuinely useful through stitch tools |
| **B: Architecture** | 1.5 (core trees) + 2 (rename) | Backbone owns shared trees; domains plug in cleanly |
| **C: Value** | 3-7 (projectkit, planning engine, wiki, resources, UX) | Project Explorer: from vague idea to structured dossier, published to wiki, linked to real infrastructure |
