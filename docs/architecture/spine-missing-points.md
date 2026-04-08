# VOS-Workbench — Spine and Settings: Missing Points

**Status:** Superseded by `canonical-gaps.md`. Retained for attribution.

*Inverted research document.*

This file is the opposite of `spine-definition.md`.
It does **not** list what has been decided.
It lists what is **still not fully addressed** even after the current spine draft.

The purpose is to keep the remaining architectural unknowns visible before implementation starts.

---

## 1. Schema layer is still too abstract

The spine now defines major decisions, but the actual configuration objects are still underspecified.

### Still missing

- A formal schema for `workbench.yaml`
- A formal schema for `modules/*/module.yaml`
- A formal schema for `resources/*.yaml`
- A formal schema for `policy/*.yaml`
- A formal schema for `clients/*.yaml`
- A formal schema for `views/*.yaml`
- A formal schema for runtime state records

### Why this matters

Right now the architecture is readable, but not yet strongly machine-validatable.
Until these schemas exist, config drift and inconsistent files are still too easy.

---

## 2. Module type system is not pinned down yet

The module instance contract exists, but the **module type layer** is still underdefined.

### Still missing

- Where module type definitions live
- How module type schemas are discovered
- How module type versions are handled
- Whether module types are code-first or schema-first
- How module capability names are standardized
- How a module advertises optional vs required config keys
- How incompatible config versions are rejected or migrated

### Why this matters

The current design defines *instances* better than it defines *types*.
Without a clean type system, modules risk becoming one-off snowflakes.

---

## 3. Config tree filesystem contract is incomplete

Directory-per-module YAML is chosen, but the filesystem contract around it is still loose.

### Still missing

- Are module directory names human-readable aliases, UUIDs, or both?
- Is `name` unique only within a tree section, or globally?
- Are filenames fixed (`module.yaml`) or extensible?
- Which directories are reserved keywords?
- Can modules nest physically, or only logically?
- How are deleted modules tombstoned, if at all?
- What is the canonical relative path resolution rule for references?

### Why this matters

The repo layout is chosen, but the path semantics are not frozen yet.

---

## 4. Reference syntax needs a real grammar

The draft uses forms like `module://policy-main` and `model://model-claude`, but the URI grammar is not formalized.

### Still missing

- Canonical grammar for `module://`, `resource://`, `model://`, `system://`, `secret://`
- Whether references point to names, UUIDs, or both
- How references are normalized internally
- Whether aliases are allowed
- How broken references are represented
- Whether references may target selectors, not only concrete instances

### Why this matters

Reference syntax is the connective tissue of the whole system. It should not remain informal.

---

## 5. Settings merge semantics are not defined

Settings precedence is now defined, but merge behavior is not.

### Still missing

- How maps merge across layers
- How arrays merge across layers
- How a lower layer explicitly removes an inherited value
- Whether `null` means remove, empty, or inherit
- Whether list items are replaced wholesale or merged by identity
- How schema validation interacts with inherited partial values

### Why this matters

Precedence without merge rules still leaves ambiguity during actual resolution.

---

## 6. Managed vs bootstrap vs local file locations are not fixed

The logical layers exist, but the physical files and lookup order do not.

### Still missing

- Where managed policy files live
- Where bootstrap config lives
- Where machine-local overrides live
- Which of those locations are Git-tracked vs Gitignored
- Whether a missing local override file is normal or an error
- Whether environment variables may override all file-based settings

### Why this matters

The conceptual model exists, but the operator experience is not defined yet.

---

## 7. Secrets model still needs operational rules

Secret references are decided. Secret behavior is not.

### Still missing

- How secret providers are registered
- Whether secret resolution happens at startup or lazily
- How secret lookup failures are reported
- Whether resolved secrets are cached in memory
- Whether secret values are ever written into artifacts or debug logs
- Whether secret references are allowed in runtime overrides
- How secret rotation is handled without restart

### Why this matters

“Secret refs only” is correct, but not enough for a real settings system.

---

## 8. Policy language is still only a first slice

The current policy syntax is a good start, but not a full rule language yet.

### Still missing

- Match syntax for module UUID, module name, capability, or tag
- Match syntax for target host/resource identity
- Match syntax for provider/model family
- Match syntax for user/operator identity
- Time-based or environment-based conditions
- Whether regex is allowed or only globs
- Rule grouping and inheritance
- How deny rules interact across layers
- Whether there are audit-only or warn-only effects
- Whether rules can mutate inputs, or only allow/deny/ask

### Why this matters

The syntax now proves the concept, but the full governance model is not yet specified.

---

## 9. Runtime bus semantics are still vague

The communication model is chosen as mixed, but the event bus is still underdefined.

### Still missing

- In-process bus only, or optional external bus backend
- Event ordering guarantees
- Delivery semantics: at-most-once, at-least-once, exactly-once not required but documented
- Event retention policy
- Event replay behavior
- Correlation ID / causality chain format
- Whether all events are persisted, or only selected classes
- Backpressure handling for noisy modules

### Why this matters

A bus is not just a concept. It needs behavioral guarantees.

---

## 10. Runtime database contract is still missing

SQLite is now the right default, but the storage model is not specified enough yet.

### Still missing

- Core tables/entities
- Migration strategy
- How actual state snapshots are stored
- How event indexes relate to artifact files
- Whether transcripts live in DB, files, or both
- Whether memory metadata and memory content are separated
- How durable runtime state is garbage-collected

### Why this matters

Choosing SQLite solves infrastructure burden, but not schema burden.

---

## 11. Persistent module lifecycle is still underdefined

Ephemeral lifecycle is in better shape than persistent lifecycle.

### Still missing

- Persistent module lifecycle states
- Startup ordering
- Restart policy
- Healthcheck contract
- Degraded vs failed distinction
- Whether a persistent module can be hot-reloaded
- What happens when a dependency disappears at runtime

### Why this matters

The system will mostly be composed of persistent modules. Their lifecycle needs equal rigor.

---

## 12. Ephemeral lifecycle still needs operational details

Budget inheritance is a strong addition, but the mechanics are still incomplete.

### Still missing

- Exact budget model: tokens, time, cost, tool calls, or multiple
- How parent budgets are divided between children
- Whether child modules may request additional budget
- What happens on budget exhaustion
- Whether paused/resumed workers keep or reset budget
- Whether parent cancellation always cascades downward
- Whether siblings may continue if one child fails catastrophically

### Why this matters

The shape is good, but the real safety comes from the exact budget rules.

---

## 13. Selector resolution is still underspecified

Selectors are allowed as an escape hatch, but their behavior is still loose.

### Still missing

- Selector matching algorithm
- Tie-breaker rules
- Whether selectors choose one instance or many
- Whether selection is deterministic or scored
- How degraded candidates are filtered
- Whether policy can veto selector resolution

### Why this matters

Selectors are where hidden magic can creep back in if left undefined.

---

## 14. Relationship between modules and nodes is still fuzzy

The repo has both a module model and a node schema, but the exact relationship is still not frozen.

### Still missing

- Is every module also a node?
- Are nodes only a UI/runtime projection layer?
- Are config roots and runtime roots represented as nodes or containers outside the module system?
- Can non-module objects (task, log, artifact) appear in the same universal tree?
- Is the node system authoritative or derivative?

### Why this matters

This is a key structural question. The architecture currently implies both a module tree and a node tree without fully unifying them.

---

## 15. Client and view settings are barely defined

The architecture says clients are secondary, but they still need a settings model.

### Still missing

- TUI view schema
- Desktop view schema
- Web observer schema
- Whether layouts are per-project, per-user, or per-client
- How view state persists
- Whether hidden branches are just presentation or true deactivation

### Why this matters

Even if UI is secondary, it still consumes settings and exposes the tree.

---

## 16. Multi-project and workspace scope is not described

The current docs largely assume one project.

### Still missing

- How multiple projects are discovered
- Whether one runtime hosts multiple projects
- Whether events are project-local or runtime-global
- Whether modules can be shared across projects
- Whether secrets and resources can be shared across projects safely

### Why this matters

This affects root manifest assumptions and long-term host architecture.

---

## 17. Reconciliation engine remains conceptual

Desired / actual / effective state is defined, but the reconciler is still abstract.

### Still missing

- What triggers reconciliation
- Whether reconciliation is push-based, poll-based, or both
- How partial convergence is retried
- Whether reconciliation is global or per subtree
- How reconciliation conflicts are surfaced to operators
- Whether reconciliation actions themselves emit events

### Why this matters

Without this, self-configuration is still philosophy rather than runtime behavior.

---

## 18. Artifact model is still incomplete

Artifacts are mentioned as filesystem-backed, but their structure and retention are not.

### Still missing

- Canonical artifact directory layout
- Retention policy
- Naming convention for artifacts
- Linkage between artifacts and tasks/events/modules
- Whether artifacts are immutable after write
- Whether artifacts can be promoted into long-term memory

### Why this matters

Artifacts are part of the real spine because they connect runtime work to durable evidence.

---

## 19. Error model and observability model are not frozen

The system has health and events, but not yet a formal error contract.

### Still missing

- Standard runtime error object shape
- User-visible vs internal error distinction
- Retryable vs terminal failure classification
- Log levels and structured logging format
- Metrics surface
- Module health reporting schema

### Why this matters

Without a standard failure model, runtime behavior will become inconsistent quickly.

---

## 20. Freeze boundary is not defined

The current docs say the spine is draft and awaiting freeze, but not how freeze happens.

### Still missing

- Which documents are authoritative
- Which documents are supporting research only
- What constitutes a frozen decision
- How a frozen decision can be reopened
- Whether schema changes require version bumps

### Why this matters

Research phase needs a formal boundary or it never really ends.

---

## Short summary

The big architectural decisions are now mostly present.
The biggest remaining gaps are in the **contracts beneath the decisions**:

- concrete schemas
- reference grammar
- merge semantics
- policy language depth
- runtime DB and event guarantees
- lifecycle details
- module/node relationship
- reconciler behavior
- artifact/error contracts

That means the **spine direction is much clearer**, but the **spine interfaces are not frozen yet**.

---

## Recommended next research targets

If the goal is to keep working only on spine and settings, the next documents should probably be:

1. `settings-model.md`
2. `reference-grammar.md`
3. `module-type-system.md`
4. `runtime-storage-contract.md`
5. `event-bus-contract.md`
6. `policy-language.md`
7. `module-vs-node-model.md`
8. `reconciler-contract.md`

---

*This file exists to show what is still missing, not to undermine what is already decided.*
