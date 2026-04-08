# VOS-Workbench — Interface Map for the 5 Custom Contracts

**Status:** Aligned — interface requirements still valid. Implementations
now defined in `alpha-proposals.md`.

*Inverse approach: instead of defining what these 5 things ARE, this document
maps what CALLS them, what VALUES flow through them, what ATTRIBUTES are
read/written, and what BREAKS if they don't exist.*

*The shape of the hole defines the piece that fills it.*

---

## 1. Module / Resource / Node Ontology

### Who calls it

| Caller | What it needs to know |
|--------|----------------------|
| Config loader (Pydantic) | Which schema validates `modules/*/module.yaml` vs `resources/*.yaml`? |
| Module type registry (entry_points) | Is this type a module, resource, or something else? |
| Wiring resolver | Can a module reference a resource? Can a node reference a module? |
| URI resolver | What does `module://x` resolve to vs `resource://x`? |
| Event bus | Event `source` field — is it a module UUID, resource name, or node ID? |
| Policy engine | Do rules match against module types, resource types, or node types? |
| Reconciler | Which objects have desired/actual state? All three? Only modules? |
| SQLite storage | What tables represent these? One table with a `kind` column, or separate tables? |
| Frontend API | What is the project tree? What objects can be navigated? |
| Runtime tree builder | Are tasks/sessions/artifacts nodes? How do they relate to modules? |

### What attributes are accessed

| Attribute | Read by | Written by |
|-----------|---------|------------|
| `kind` (module / resource / node) | Everything — this is the discriminator | Config loader at parse time |
| `uuid` | Wiring, events, storage, API, policy | Config loader (persistent) or runtime (ephemeral) |
| `name` | Wiring (explicit refs), API, UI | Config files |
| `type` (e.g. `core.router`, `exec.ssh`) | Registry, policy matcher, selector | Config files |
| `config` / `spec` | Module startup, validation, reconciler | Config files, merge engine |
| `status` | Reconciler, health, API | Runtime observation |
| `lifecycle` (persistent / ephemeral) | Startup sequence, cleanup, reconciler | Config files (persistent) or spawner (ephemeral) |
| `activation_state` (inactive/available/active/degraded) | Health, API, event bus | Runtime, reconciler |
| `parent_id` | Tree navigation, budget inheritance | Spawner (for ephemeral), config (for persistent) |
| `children` | Tree navigation, UI | Runtime tree builder |
| `capabilities` | Selector resolution, wiring | Module type manifest |
| `depends_on` | Bootstrap sequence (topo sort), wiring | Config files |
| `provides` | Selector resolution | Module type manifest |

### What functions must exist

```
# Identity
get_by_uuid(uuid) -> Module | Resource | Node
get_by_name(name, kind?) -> Module | Resource | Node
list_by_kind(kind) -> list
list_by_type(type_name) -> list
list_by_capability(capability) -> list

# Lifecycle
create(kind, spec) -> uuid
delete(uuid)
get_status(uuid) -> ActivationState
set_status(uuid, state)

# Tree
get_children(uuid) -> list
get_parent(uuid) -> uuid | None
get_tree(root?) -> nested structure

# Type checking
is_module(uuid) -> bool
is_resource(uuid) -> bool
is_node(uuid) -> bool
get_kind(uuid) -> str
```

### What breaks without it

- Config loader doesn't know which schema to apply to which file
- Wiring resolver can't distinguish `module://x` from `resource://x`
- Policy engine can't scope rules to module types vs resource types
- Frontend tree is a flat bag of untyped objects
- Storage has no table design

---

## 2. URI Reference Grammar

### Who calls it

| Caller | What it resolves |
|--------|-----------------|
| Config loader | `module://policy-main` in module.yaml `wiring.depends_on` |
| Config loader | `secret://env/ANTHROPIC_API_KEY` in provider config |
| Config loader | `system://eventbus` in module config |
| Wiring resolver | All `module://` and `resource://` refs → actual objects |
| Secret resolver | All `secret://` refs → actual secret values |
| Policy engine | References in policy `match` fields |
| Selector resolver | `capability://routing` → find modules providing this |
| Frontend API | Returns URIs in responses, accepts them in requests |
| Event bus | Event `source` may be a URI |
| Reconciler | Compares desired refs with actual resolved state |
| Error reporter | Includes broken URI in error messages |

### What values flow through

| Direction | Type | Example |
|-----------|------|---------|
| **Input** | Raw string | `"module://policy-main"` |
| **Parsed** | Structured reference | `{scheme: "module", path: "policy-main"}` |
| **Resolved** | Python object or value | `<PolicyModule uuid=abc>` or `"sk-ant-..."` |
| **Error** | Unresolvable reference | `{uri: "module://missing", reason: "not found"}` |
| **Serialized** | Canonical string | `"module://policy-main"` (normalized) |

### What the parser must handle

| Scheme | Path format | Resolves to | Example |
|--------|------------|-------------|---------|
| `module` | name or UUID | Module instance | `module://policy-main` |
| `resource` | name | Resource declaration | `resource://proxmox` |
| `secret` | provider/key | Secret value (never serialized back) | `secret://env/API_KEY` |
| `system` | service name | System-level singleton | `system://eventbus` |
| `capability` | capability name | Set of modules providing it | `capability://routing` |

### What functions must exist

```
# Parsing
parse(uri_string) -> Reference
validate(uri_string) -> bool | Error
normalize(uri_string) -> str

# Resolution
resolve(reference, registry) -> object | value
resolve_or_error(reference, registry) -> object | UnresolvableError
is_resolvable(reference, registry) -> bool

# Serialization
to_string(reference) -> str

# Batch
resolve_all(config_dict, registry) -> resolved_dict  # walk a config tree, resolve all URIs
find_all_references(config_dict) -> list[Reference]  # extract all URIs from a config tree
find_broken(config_dict, registry) -> list[Reference] # find all unresolvable URIs
```

### What breaks without it

- Config files contain strings like `module://x` that are never parsed
- Wiring is just string matching, not actual object resolution
- Secrets are never resolved — modules can't get API keys
- Broken references are silent failures
- No way to validate a config tree's references before starting

---

## 3. Settings Precedence and Merge Rules

### Who calls it

| Caller | What it needs |
|--------|--------------|
| Config loader | Merge 5 layers into one effective config per module |
| Module startup | Read effective config |
| Hot-reload watcher | Re-merge on file change, diff against previous effective |
| Policy engine | Policies merge across layers too (managed policy wins) |
| Reconciler | Compares effective config (desired) with runtime actual |
| Frontend API | May expose which layer a value came from (for debugging) |
| Validation | Validate the merged result, not individual layers |
| Secret resolver | Secrets appear in config layers — must survive merge |

### What values flow through

| Direction | Type | Example |
|-----------|------|---------|
| **Input** | Dict per layer | `{managed: {...}, bootstrap: {...}, project: {...}, local: {...}, runtime: {...}}` |
| **Output** | Single effective dict | `{mode: "planning", max_agents: 4, ...}` |
| **Trace** | Value + source layer | `("planning", "project")` |
| **Diff** | Old effective vs new effective | `[{key: "mode", old: "planning", new: "execution", layer: "runtime"}]` |

### Merge rules (must be implemented)

| Data type | Rule | Example |
|-----------|------|---------|
| Scalar | Higher layer replaces lower | `runtime.mode = "execution"` replaces `project.mode = "planning"` |
| Dict | Deep merge, higher keys win | `{a: 1, b: 2}` + `{b: 3, c: 4}` → `{a: 1, b: 3, c: 4}` |
| List | Replace wholesale (not append) | `project.tags: [a, b]` + `local.tags: [c]` → `[c]` |
| `null` | Explicit remove | `local.debug: null` removes `project.debug: true` |
| Secret ref | Survives merge, resolved separately | `secret://env/KEY` passes through merge unchanged |

### What functions must exist

```
# Core merge
merge_layers(managed, bootstrap, project, local, runtime) -> effective
merge_two(base, override) -> merged  # recursive dict merge with rules above

# Tracing
trace_value(effective, key_path) -> (value, source_layer)
trace_all(effective) -> dict[key_path, source_layer]

# Diffing
diff_effective(old, new) -> list[Change]

# Validation
validate_effective(effective, schema) -> list[Error]

# Reload
reload_layer(layer_name) -> new_layer_dict
recompute_effective(layers) -> new_effective
```

### What breaks without it

- Two layers define the same key — which wins? Undefined behavior
- A module gets config from an unknown layer — can't debug
- A list in project config gets appended by local config — unexpected behavior
- `null` in a layer is ambiguous — is it "remove" or "I didn't set this"?
- Hot-reload recomputes but nobody knows what changed

---

## 4. Ephemeral Budget Inheritance

### Who calls it

| Caller | What it needs |
|--------|--------------|
| Router/coordinator | Split parent budget among N children |
| Ephemeral worker | Check remaining budget before each LLM call |
| Agent loop (borrowed from CC) | Check `budget.is_exhausted()` before calling model |
| Tool executor | Report tool-call cost against budget |
| Event bus | Emit `budget.exhausted` event |
| Pre-planner | Decide how to divide budget for fan-out |
| Frontend API | Expose budget status per worker |
| Cleanup handler | Trigger graceful stop on exhaustion |
| Parent coordinator | Receive child's remaining budget on completion (reclaim?) |

### What values flow through

| Direction | Type | Example |
|-----------|------|---------|
| **Created** | Budget envelope | `{tokens: 50000, seconds: 300, tool_calls: 100}` |
| **Split** | N child budgets from parent | Parent 50000 tokens → 3 children × ~16000 each |
| **Consumed** | Usage report | `{tokens_used: 1200, seconds_elapsed: 3.2, calls_used: 1}` |
| **Remaining** | Budget status | `{tokens: 48800, seconds: 296.8, tool_calls: 99}` |
| **Exhausted** | Trigger | Any dimension hits zero |
| **Extension request** | Child → parent | `{worker_uuid: "...", requested_tokens: 10000}` |
| **Extension response** | Parent → child | `Budget(tokens=10000)` or `Denied(reason="parent exhausted")` |

### What functions must exist

```
# Creation
create_budget(tokens=None, seconds=None, tool_calls=None) -> Budget
create_unlimited() -> Budget  # for persistent modules / manual use

# Splitting
split_equal(parent, num_children) -> list[Budget]
split_weighted(parent, weights: list[float]) -> list[Budget]
allocate(parent, request: Budget) -> Budget | Denied

# Consumption
consume(budget, usage: Usage) -> Budget  # returns updated budget
is_exhausted(budget) -> bool
remaining(budget) -> BudgetRemaining
which_exhausted(budget) -> list[str]  # ["tokens"] or ["seconds", "tool_calls"]

# Extension
request_extension(child_id, amount: Budget) -> Budget | Denied
reclaim(child_id) -> Budget  # get back unused budget from completed child

# Events
on_exhaustion(budget, worker_id) -> ExhaustionAction  # graceful_stop | hard_kill
on_warning(budget, threshold_pct) -> WarningEvent  # e.g., 80% consumed
```

### What breaks without it

- Ephemeral agent runs forever, burns all API credits
- Pre-planner spawns 10 agents, no way to limit total cost
- Agent finishes early, unused budget is wasted (no reclaim)
- No visibility into how much budget each agent used
- No graceful shutdown — just hard timeout or infinite run

---

## 5. Desired / Actual / Effective State Model

### Who calls it

| Caller | What it needs |
|--------|--------------|
| Config loader | Provides desired state (parsed from YAML) |
| Settings merge engine | Provides effective state (desired after precedence + policy) |
| Runtime | Provides actual state (observed from running modules) |
| Reconciler | Computes diff between effective and actual, applies actions |
| Event bus | Emits `state.changed`, `state.drifted`, `state.converged` |
| Frontend API | Exposes all three states + convergence status per scope |
| Health system | Module health is part of actual state |
| SQLite storage | Persists actual state snapshots + convergence history |
| Policy engine | May block state transitions (policy says module can't be disabled) |
| Rollback handler | Needs previous desired state to revert |

### What values flow through

| Direction | Type | Example |
|-----------|------|---------|
| **Desired** | Parsed from config YAML | `{module: "router-main", config: {mode: "planning"}}` |
| **Effective** | Desired after merge + policy | `{module: "router-main", config: {mode: "planning"}, policy_applied: [...]}` |
| **Actual** | Observed from runtime | `{module: "router-main", status: "active", config_hash: "abc123"}` |
| **Diff** | List of differences | `[{path: "config.mode", desired: "execution", actual: "planning"}]` |
| **Convergence** | Status enum | `converged | pending | degraded | drifted | failed` |
| **Action** | What to do about a diff | `{type: "reconfigure", target: uuid, changes: [...]}` |
| **Result** | Outcome of an action | `{action_id: "...", success: true}` |
| **History** | Previous states for rollback | `[{version: 3, desired: {...}, timestamp: "..."}]` |

### State transitions

```
                    config change
                         │
                         v
converged ──────────→ pending
    ↑                    │
    │              ┌─────┼─────┐
    │              v     v     v
    │          converged degraded failed
    │              │               │
    │              └───────────────┘
    │                     │
    │                  drifted ←── runtime changed without config change
    │                     │
    └─────────────────────┘
              reconciler fixes drift
```

### What functions must exist

```
# State access
get_desired(scope: uuid | "global") -> StateTree
get_effective(scope) -> StateTree  # desired after merge + policy
get_actual(scope) -> StateTree     # observed from runtime
get_convergence(scope) -> ConvergenceStatus

# Diffing
compute_diff(effective, actual) -> list[Diff]
has_drift(scope) -> bool

# Reconciliation
plan_actions(diffs: list[Diff]) -> list[Action]  # dry-run
apply_actions(actions: list[Action]) -> list[Result]
reconcile(scope) -> ConvergenceStatus  # plan + apply in one call

# History
get_state_history(scope, limit) -> list[StateSnapshot]
rollback(scope, to_version) -> Result

# Events
emit_state_change(scope, old_status, new_status)
emit_drift_detected(scope, diffs)
emit_convergence_failed(scope, reason)

# Persistence
save_actual_snapshot(scope, state)
save_convergence_status(scope, status)
```

### What breaks without it

- Config changes happen but nothing checks if they took effect
- A module crashes and nobody notices the drift
- No way to answer "is the system in the state I asked for?"
- No rollback — if a config change breaks things, manual repair only
- Frontend shows desired state as if it's real — user thinks system is healthy when it's not

---

## Cross-reference: what connects to what

```
                    ┌─────────────────┐
                    │  Config Files   │
                    │  (YAML on disk) │
                    └────────┬────────┘
                             │ parse
                             v
                    ┌─────────────────┐
              ┌────→│  URI Grammar    │←────┐
              │     │  (parse/resolve)│     │
              │     └────────┬────────┘     │
              │              │ resolve      │
              │              v              │
     ┌────────┴───────┐  ┌──────────┐  ┌───┴──────────┐
     │   Ontology      │  │ Secrets  │  │   Wiring     │
     │ (module/res/node)│  │ resolver │  │   resolver   │
     └────────┬────────┘  └──────────┘  └───┬──────────┘
              │                              │
              v                              v
     ┌─────────────────┐          ┌─────────────────┐
     │ Settings Merge   │          │ Module Registry  │
     │ (5-layer merge)  │          │ (entry_points)   │
     └────────┬─────────┘          └────────┬────────┘
              │ effective                    │ instantiate
              v                              v
     ┌─────────────────────────────────────────────┐
     │              Runtime                         │
     │  ┌──────────┐  ┌─────────┐  ┌────────────┐ │
     │  │ Modules   │  │ Event   │  │ Budget     │ │
     │  │ (running) │  │ Bus     │  │ Tracker    │ │
     │  └─────┬─────┘  └────┬────┘  └─────┬──────┘ │
     │        │              │              │        │
     │        v              v              v        │
     │  ┌─────────────────────────────────────────┐ │
     │  │     Desired / Actual / Effective         │ │
     │  │         State Model                      │ │
     │  │    (reconciler consumes all above)        │ │
     │  └──────────────────────────────────────────┘ │
     └──────────────────────────────────────────────┘
```

All 5 contracts are interconnected. The ontology defines WHAT exists.
The URI grammar defines HOW things reference each other. The merge rules
define HOW config layers combine. The budget system defines HOW ephemeral
workers are constrained. The state model defines HOW the system knows
if reality matches intent. Remove any one and the others lose their anchor.

---

*This document defines each contract from the outside in. The implementations
should satisfy these interfaces — the callers, values, attributes, and
functions listed here are the acceptance criteria.*
