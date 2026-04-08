# VOS-Workbench — Custom Routines Inverse Map

*Inverse design document.*

This file does **not** describe how the remaining custom routines should be implemented internally.
It describes their **outside contract**:

- what calls them,
- what data they need,
- what attributes/values they own,
- what functions they must expose,
- what they return,
- what they are explicitly **not** responsible for.

Goal: make the remaining 5 custom designs look like small interface problems instead of giant unknown subsystems.

---

## The 5 custom routines

From `steal-map.md`, only these remain truly VOS-specific:

1. Module / resource / node ontology
2. URI reference grammar
3. Settings precedence and merge rules
4. Ephemeral budget inheritance
5. Desired / actual / effective state model

Everything else should be adopted or wrapped.

---

# 1. Module / Resource / Node Ontology

## Purpose

Define the core identity categories of the system so the rest of the architecture uses the same vocabulary.

## Called by

- Config loader
- Tree builder
- Runtime state projector
- API layer
- TUI / future GUI
- Reconciler
- Policy engine

## Must consume

- Parsed config objects
- Runtime objects
- Resource declarations
- Module instances
- Task/session/artifact objects

## Must expose

### Functions

- `classify_object(obj) -> OntologyKind`
- `is_module(obj) -> bool`
- `is_resource(obj) -> bool`
- `is_node(obj) -> bool`
- `project_to_node(obj) -> NodeView`
- `get_identity(obj) -> IdentityRef`
- `get_parent_scope(obj) -> ParentRef | None`

### Core values / enums

- `OntologyKind = module | resource | node`
- `NodeKind = project | container | task | session | artifact | log | memory | module_view | resource_view | worker`
- `ModuleLifecycle = persistent | ephemeral`
- `ResourceKind = shell | ssh_host | api_provider | git_repo | model_provider | datastore | external_service`

## Must own these attributes

### For a module
- `uuid`
- `name`
- `type`
- `lifecycle`
- `enabled`

### For a resource
- `resource_id`
- `name`
- `resource_type`
- `connection_scope`
- `external = true`

### For a node
- `node_id`
- `node_type`
- `label`
- `parent_id`
- `activation_state`
- `backing_ref` (module/resource/task/etc.)

## Must return

- canonical identity references
- normalized node projections for UI/API
- ontology validation errors when an object violates category rules

## Must NOT own

- storage
- module execution
- config merging
- event transport
- UI rendering

## Design test

If the question is:
- “what *is* this thing?” → ontology answers
- “how do I display it?” → node projection answers
- “how do I execute it?” → not ontology

---

# 2. URI Reference Grammar

## Purpose

Define the reference language used across config and runtime.

## Called by

- Config validator
- Module loader
- Dependency resolver
- Secret resolver
- Reconciler
- Policy engine
- API serialization/deserialization

## Must consume

- raw URI/reference strings from config
- context for resolution (project scope, runtime scope, registry)

## Must expose

### Functions

- `parse_ref(text) -> ParsedRef`
- `validate_ref(text, expected_kind=None) -> ValidationResult`
- `resolve_ref(parsed_ref, context) -> ResolutionResult`
- `normalize_ref(parsed_ref) -> CanonicalRef`
- `is_selector_ref(parsed_ref) -> bool`
- `ref_kind(parsed_ref) -> RefKind`

### Core values / enums

- `RefKind = module | resource | secret | system | capability | model`
- `ResolutionStatus = resolved | unresolved | ambiguous | forbidden`

### Supported schemes

- `module://...`
- `resource://...`
- `secret://...`
- `system://...`
- `capability://...`
- `model://...`

## Must own these attributes

For a parsed reference:
- `scheme`
- `target`
- `selector_fields` (optional)
- `raw`
- `normalized`
- `scope`

## Must return

- typed parsed reference object
- canonical normalized reference string
- resolved target identity or structured failure

## Must NOT own

- actual secret fetching logic
- module startup logic
- selector scoring policy
- config precedence

## Design test

If a string can appear in config and point to something else, URI grammar owns the syntax.
If code needs to know what the target *does*, URI grammar stops and the resolver/registry continues.

---

# 3. Settings Precedence and Merge Rules

## Purpose

Turn layered config into one effective configuration without ambiguity.

## Called by

- Config loader
- Module instantiation
- Runtime overrides
- Reconciler
- Hot-reload logic
- API mutation endpoints

## Must consume

- managed settings layer
- bootstrap settings layer
- project settings layer
- machine-local settings layer
- runtime/session override layer
- schema information / type information

## Must expose

### Functions

- `merge_layers(layers) -> EffectiveConfig`
- `apply_precedence(base, override) -> Config`
- `remove_value(config, path) -> Config`
- `resolve_defaults(config, schema) -> Config`
- `diff_layers(layers) -> ConfigDiff`
- `explain_effective_value(path, layers) -> ValueTrace`

### Core values / enums

- `ConfigLayer = managed | bootstrap | project | local | runtime`
- `MergeMode = replace | deep_merge | keyed_merge | remove`
- `HotReloadSupport = none | project_only | local_and_runtime | full`

## Must own these attributes

For each effective value:
- `value`
- `source_layer`
- `source_path`
- `defaulted` (bool)
- `removed` (bool)

For a merge decision:
- `merge_mode`
- `path`
- `winner_layer`
- `loser_layers`

## Must return

- one normalized effective config object
- merge trace/explanation for debugging
- validation errors if merge produces invalid config

## Must NOT own

- file IO itself
- secret fetching
- module execution
- persistent storage schema

## Design test

If two settings disagree, this routine decides which one wins.
If a module cannot start because config is invalid, this routine should be able to explain exactly why.

---

# 4. Ephemeral Budget Inheritance

## Purpose

Define the safety envelope for spawned workers/agents.

## Called by

- Router / coordinator module
- Worker spawner
- Runtime scheduler
- Policy engine
- Cancellation logic
- Observability layer

## Must consume

- parent task/session identity
- parent budget envelope
- spawn request
- worker type/class
- optional requested override

## Must expose

### Functions

- `inherit_budget(parent_budget, spawn_request) -> ChildBudget`
- `split_budget(parent_budget, strategy, n_children) -> BudgetAllocation[]`
- `check_budget(worker_state, usage) -> BudgetStatus`
- `request_budget_extension(worker_id, amount) -> ExtensionDecision`
- `consume_budget(worker_id, usage_event) -> BudgetLedger`
- `finalize_budget(worker_id) -> BudgetSummary`

### Core values / enums

- `BudgetKind = tokens | wall_clock | tool_calls | cost_units`
- `BudgetStatus = ok | nearing_limit | exhausted | timed_out | cancelled`
- `ExtensionDecision = granted | denied | escalate`
- `SplitStrategy = equal | weighted | reserved_pool | manual`

## Must own these attributes

For each worker budget:
- `worker_id`
- `parent_id`
- `token_limit`
- `time_limit_ms`
- `tool_call_limit` (optional)
- `cost_limit` (optional)
- `remaining`
- `inherited_from`
- `extension_policy`

## Must return

- concrete child budget envelope
- current budget status
- exhaustion / timeout reason
- end-of-life budget summary

## Must NOT own

- token counting implementation inside model providers
- task orchestration policy
- subprocess lifecycle
- billing system logic

## Design test

If a child worker runs wild, this routine is what stops it.
If the parent asks “how much runway do my children still have?”, this routine answers.

---

# 5. Desired / Actual / Effective State Model

## Purpose

Define the three-state lens used by the reconciler and operator views.

## Called by

- Reconciler
- API layer
- Runtime health view
- TUI / GUI inspector
- Drift detection
- Config change planner

## Must consume

- desired config tree
- observed runtime state
- settings precedence output
- dependency resolution output
- policy decisions affecting effective behavior

## Must expose

### Functions

- `compute_desired(config_tree) -> DesiredState`
- `observe_actual(runtime_snapshot) -> ActualState`
- `compute_effective(desired, actual, policy, resolved_config) -> EffectiveState`
- `compare_states(desired, actual) -> DriftReport`
- `compare_effective(desired, effective) -> PolicyAdjustedReport`
- `classify_convergence(desired, actual, effective) -> ConvergenceStatus`

### Core values / enums

- `ConvergenceStatus = converged | pending | degraded | drifted | failed`
- `DriftKind = missing | extra | mismatched | policy_adjusted | unresolved_dependency`

## Must own these attributes

For a state object entry:
- `object_id`
- `object_kind`
- `desired_value`
- `actual_value`
- `effective_value`
- `status`
- `last_observed_at`
- `last_changed_at`
- `drift_reason`

## Must return

- normalized desired state snapshot
- normalized actual state snapshot
- effective state snapshot
- drift report
- convergence classification per object and per subtree

## Must NOT own
n- reconciliation execution itself
- event bus transport
- storage engine
- UI rendering

## Design test

If an operator asks:
- “what should exist?” → desired
- “what actually exists?” → actual
- “what is really in force after policy and resolution?” → effective

This routine must answer all three clearly.

---

# Cross-routine call map

This is the minimal dependency picture between the 5 custom routines.

```text
URI Grammar
    -> used by Settings Merge
    -> used by Ontology classification

Ontology
    -> used by Desired/Actual/Effective model
    -> used by API/TUI projection

Settings Merge
    -> feeds Desired state
    -> feeds Effective state

Budget Inheritance
    -> used by runtime worker spawning
    -> reported into Actual/Effective state

Desired/Actual/Effective
    -> consumed by Reconciler
    -> consumed by API/TUI/health views
```

---

# Minimal implementation order

If these routines are designed one by one, the least painful order is:

1. **URI Grammar**
2. **Ontology**
3. **Settings Merge**
4. **Desired / Actual / Effective State**
5. **Ephemeral Budget Inheritance**

Reason:
- references and identities must exist first,
- then config can merge,
- then state can be modeled,
- then budgets can plug into runtime behavior.

---

# Short summary

The 5 custom routines are not 5 giant subsystems.
They are 5 **interface contracts**:

1. identity contract
2. reference contract
3. settings resolution contract
4. budget envelope contract
5. state interpretation contract

That is a much smaller and more buildable problem.

---

*Use this file when discussing the remaining custom design work. If a new idea does not change one of these contracts, it probably belongs in adopted/wrapped infrastructure, not custom architecture.*
