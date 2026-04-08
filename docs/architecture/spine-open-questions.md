# VOS-Workbench — Spine & Settings: Open Questions

**Status:** Superseded by `canonical-gaps.md` and `alpha-proposals.md`.
Retained as design history.

*Gap analysis produced by ChatGPT, reviewed by Claude. Captures what was
undefined after the core thesis was established.*

## What is already defined

- Modular, headless agentic backend
- Modules are UUID-based instances
- The tree/config defines the system
- Frontends are secondary
- Python is the implementation language
- First-class concepts: module, wiring, tree, memory, policy, runtime, TUI

---

## Spine: still undefined

### 1. Tree serialization format

The thesis leaves open whether the tree is:

- One YAML file
- One JSON/TOML file
- Directory-per-module
- Hybrid

This is a spine decision because everything hangs off serialization, diffs,
loading, and mutation.

### 2. Module communication model

Not yet chosen whether modules talk by:

- Direct async calls
- Message bus
- Event stream
- Actor/mailbox model
- Mixed model

Without this, "wiring" is a slogan, not a runtime design.

### 3. Wiring resolution

Not decided whether dependencies are:

- **Explicit:** module A references UUIDs directly
- **Declarative:** module A asks for a capability/type and runtime resolves it
- **Layered:** declarative by default, explicit override

One of the biggest missing backbone choices.

### 4. Persistent vs ephemeral module lifecycle

The repo says modules may be persistent or ephemeral, but does not define:

- Who spawns ephemeral modules
- Where they are tracked
- Whether they appear in the tree
- How cleanup works
- What survives after they die

Agent workers are conceptually present, but lifecycle is not defined.

### 5. Runtime state boundary

The thesis says the tree is desired state, but leaves open where actual
runtime state lives:

- Session history
- Task progress
- Live agent state
- Queues
- Memory contents
- Module health

### 6. Event bus contract

An event schema exists, but not the event architecture:

- Append-only log only, or live pub/sub too?
- Ordering guarantees
- Durability guarantees
- Replay behavior
- Per-project vs global stream
- Event correlation IDs / causality model

There is an event **shape**, not an event **spine**.

### 7. Canonical root objects

A node schema with types like `project`, `task`, `resource`, `memory`, `agent`
exists, but not the mandatory root tree:

- Which branches always exist
- Which appear lazily
- Which are virtual vs persisted
- Whether modules and nodes are the same thing or separate layers

---

## Settings: still undefined

### 8. Settings precedence

Bootstrap/project/runtime config levels exist conceptually but need a hard rule:

```
managed policy > bootstrap > project > local override > session runtime
```

Without this, config conflict resolution becomes chaos.

### 9. What settings belong where

Schemas are broad and permissive:

- `policies` is freeform
- `metadata` is freeform
- `models` is barely constrained
- Module config is not typed by module family

**Claude's note:** Intentionally loose at this stage. Define the mechanism
(module declares schema, runtime validates) rather than locking specific
schemas before module types are discovered.

### 10. Secrets model

No defined answer for:

- Where API keys live
- How modules reference secrets
- Whether secrets are file refs, env refs, or secret-provider refs
- What may be exported in tree snapshots
- What is intentionally local-only

### 11. Policy rule syntax

The concept of policies exists, but not the language:

- Allow/ask/deny syntax
- Per-tool rules
- Per-path rules
- Per-host rules
- Inheritance and precedence
- Protected paths
- Module-scoped vs project-wide policy

### 12. Module instance config schema strategy

The module contract says modules have `config_schema`, but undefined:

- Where module type schemas live
- How versioning works
- Migration rules
- Instance validation lifecycle
- How broken configs are represented

**Claude's note:** Like item 9, define the mechanism first. Specific schemas
fill in as modules get built.

### 13. Desired vs actual state model

Reconciler-style self-configuration needs a formal state split:

- **Desired** — what the tree says should be true
- **Observed** — what the runtime sees right now
- **Pending** — change in flight
- **Degraded** — partially converged
- **Failed convergence** — gave up

Without this, self-config is philosophy, not machinery.

### 14. Provider/model routing settings

Still open whether model/provider selection is:

- A router capability
- A dedicated module
- Per-task policy
- Per-agent override
- Cost/latency based
- Capability based

**Claude's note:** Defer this. It's a feature, not a spine decision. It falls
out naturally as a module once the module system works.

### 15. Local-only vs shareable settings

Need a hard line between:

- Project-shareable config
- Machine-local config
- User-personal config
- Ephemeral session state

Matters for Git, portability, and safe collaboration.

---

## Recommended lock order

Freeze these in order to turn the thesis into an actual backbone:

| Priority | Decision | Why first |
|----------|----------|-----------|
| 1 | Tree format | Everything serializes through it |
| 2 | Settings precedence | Config conflicts bite early |
| 3 | Module communication | The runtime backbone |
| 4 | Wiring resolution | Turns "modular" from concept to contract |
| 5 | Runtime state location | Separates desired from actual |
| 6 | Policy syntax | Required before execution modules get real |
| 7 | Ephemeral lifecycle | Required before multi-agent orchestration |
| 8 | Desired/actual state split | Required before self-configuration |

---

*This document captures gaps, not decisions. Each item should be resolved
through design discussion and recorded in its own architecture document
or added to the core thesis.*
