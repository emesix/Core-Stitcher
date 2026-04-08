# VOS-Workbench — Canonical Gap List

**Status:** Research — gap tracking. Most Tier 1 items now addressed
by `alpha-proposals.md`.

*Merged from Claude's `spine-remaining-gaps.md` and ChatGPT's
`spine-missing-points.md`. Gap tracker for spine and settings.*

**Rule:** When an item on this list gets resolved, record the decision in
the appropriate architecture doc and strike it from this list.

---

## Tier 1 — Must be defined before implementation starts

These block writing code. Without them, you can't load a module,
start the system, or connect a frontend.

### 1.1 Module type registry

Source: Claude S1, ChatGPT #2

- Where do module type definitions live? Python packages? Plugin directory?
- How does the runtime discover and load module types?
- Is a module type code-first or schema-first?
- What is a type manifest? (name, version, config schema, entry point,
  capabilities, required vs optional config keys)
- Can third-party module types be installed?
- How are module capability names standardized?

### 1.2 Bootstrap and startup sequence

Source: Claude S2, ChatGPT #11

- Dependency resolution algorithm (topological sort?)
- Circular dependency handling
- Startup timeout per module
- What happens when a dependency fails to start?
- Persistent module lifecycle states (not just ephemeral)
- Restart policy for persistent modules
- Healthcheck contract

### 1.3 Reference and URI grammar

Source: Claude C9, ChatGPT #4

- Canonical grammar for all schemes: `module://`, `resource://`, `model://`,
  `system://`, `secret://`, `capability://`
- Do references point to names, UUIDs, or both? Are aliases allowed?
- How are references normalized internally?
- How are broken references represented and reported?
- Can references target selectors, not only concrete instances?
- When are references resolved — config load time or first use?

### 1.4 Modules vs nodes vs resources

Source: Claude S8/C5, ChatGPT #14

This is a structural fork that must be decided:

- Is every module also a node?
- Are nodes a UI/runtime projection layer on top of modules?
- Are resources just modules of type `resource.*`, or a separate concept?
- Can non-module objects (task, log, artifact) appear in the module tree?
- Is the node schema (`node.schema.json`) authoritative or derivative?
- One unified tree, or modules + nodes as separate layers?

### 1.5 Event bus contract

Source: Claude S3, ChatGPT #9

"pubsub" is not a spec. Define:

- Subscription mechanism (how does a module subscribe?)
- Delivery guarantees (at-most-once / at-least-once)
- Ordering (per-source ordered? globally ordered?)
- Durability (which events persist? how long?)
- Replay (can a new subscriber catch up?)
- Filtering (by event type, source, tags?)
- Correlation (parent event ID / causality chain)
- Backpressure (what happens when a subscriber is slow?)
- Scope (per-project? global? both?)
- In-process only, or optional external backend (NATS, Redis)?

### 1.6 Frontend API contract

Source: Claude S4

- Protocol: REST? WebSocket? gRPC? Combination?
- Authentication: how does a frontend prove identity?
- Authorization: can different frontends have different permissions?
- Streaming: how does the frontend receive live updates?
- Session model: does a frontend session map to a runtime session?

### 1.7 Config validation, merge, and reload semantics

Source: Claude C1/C2/C3, ChatGPT #5

**Validation:**
- When is config validated? File load? Module instantiation? Both?
- What happens on validation failure?
- Can a module start with partial config?

**Merge:**
- How do maps merge across precedence layers?
- How do arrays merge? Replace or append?
- Does `null` mean remove, empty, or inherit?
- How does schema validation interact with partial inherited values?

**Reload:**
- Which layers support hot-reload? (Not bootstrap.)
- How does a module learn its config changed?
- Is there a config-changed event on the bus?
- Can a module reject a config change?

**Defaults:**
- Where do defaults come from? Module type definition? Code? Defaults file?
- Applied before or after precedence merging?

### 1.8 Concurrency and supervision model

Source: Claude S9

- Single-process async (asyncio) or multi-process?
- Can modules block the event loop? What prevents it?
- Isolation boundary between modules (async tasks? subprocesses? containers?)
- Shared state protection strategy
- Supervision strategy for module failures (Erlang-style?)

### 1.9 Runtime storage contract

Source: ChatGPT #10

SQLite is chosen, but the schema is not:

- Core tables/entities
- Migration strategy
- How actual-state snapshots are stored
- How event indexes relate to artifact files
- Whether transcripts live in DB, files, or both
- Whether memory metadata and content are separated
- Garbage collection for durable runtime state

### 1.10 Error propagation model

Source: Claude S5, ChatGPT #19

- Standard error object shape
- User-visible vs internal error distinction
- Retryable vs terminal failure classification
- How does a module failure propagate to dependents?
- Does the runtime attempt restarts? How many times?
- How are errors surfaced to frontends?
- How are ephemeral agent failures reported to the pre-planner?

---

## Tier 2 — Must be defined before the system is scalable or safe

These don't block a proof-of-concept but block production use,
multi-agent orchestration, and real security.

### 2.1 Policy language expansion

Source: ChatGPT #8

Current syntax proves the concept. Still needed:

- Match by module UUID, name, capability, or tag
- Match by target host/resource identity
- Match by provider/model family
- Match by user/operator identity
- Time-based or environment-based conditions
- Rule grouping and inheritance
- Audit-only or warn-only effects
- Whether rules can mutate inputs, not just allow/deny/ask

### 2.2 Secret resolution lifecycle

Source: ChatGPT #7

- How are secret providers registered?
- Startup resolution or lazy?
- How are lookup failures reported?
- Are resolved secrets cached in memory?
- Are secret values ever written to artifacts or debug logs? (Must be no.)
- How is secret rotation handled without restart?

### 2.3 Selector resolution rules

Source: ChatGPT #13

- Matching algorithm
- Tie-breaker rules
- One instance or many?
- Deterministic or scored?
- How are degraded candidates filtered?
- Can policy veto selector resolution?

### 2.4 Ephemeral lifecycle operational details

Source: ChatGPT #12

Budget model still needs:

- Budget dimensions: tokens, time, cost, tool calls, or multiple?
- How parent budgets divide between children
- Whether children may request additional budget
- What happens on budget exhaustion (graceful stop? hard kill?)
- Whether paused/resumed workers keep or reset budget
- Whether parent cancellation always cascades
- Whether siblings continue if one sibling fails

### 2.5 Artifact model

Source: ChatGPT #18

- Canonical directory layout
- Retention policy
- Naming convention
- Linkage between artifacts and tasks/events/modules
- Immutability after write?
- Promotion path to long-term memory?

### 2.6 Observability and logging

Source: Claude C8, ChatGPT #19

- Structured logging format (JSON?)
- Log levels per module
- Log routing (file, stdout, external service)
- Module-level metrics exposure
- Distributed tracing across module calls?

### 2.7 Multi-project scope

Source: Claude C7, ChatGPT #16

- Can one backend serve multiple projects?
- How are projects isolated?
- Shared modules across projects?
- Shared secrets/resources?
- Or explicitly single-project for now?

### 2.8 Clients and views

Source: Claude C6, ChatGPT #15

- What is a client config?
- What is a view config?
- Per-project, per-user, or per-client?
- Are these backend settings or purely frontend concerns?

---

## Tier 3 — Governance and long-term maintainability

### 3.1 Config file locations

Source: ChatGPT #6

- Where managed policy files physically live
- Where bootstrap config physically lives
- Where machine-local overrides physically live
- Which are Git-tracked vs gitignored
- Whether env vars can override all file-based settings

### 3.2 Config inheritance between instances

Source: Claude C4

- Can module instances inherit from a base/template config?
- Example: 5 SSH modules sharing most settings but differing in host
- If inheritance exists, how deep can it go?

### 3.3 Filesystem contract details

Source: ChatGPT #3

- Are module directory names aliases, UUIDs, or both?
- Is `name` unique within a section or globally?
- Are filenames fixed (`module.yaml`) or extensible?
- Reserved directory names?
- Physical nesting of modules?
- Tombstoning deleted modules?

### 3.4 Formal schemas

Source: ChatGPT #1

JSON Schema or Pydantic models needed for:

- `workbench.yaml`
- `modules/*/module.yaml`
- `resources/*.yaml`
- `policy/*.yaml`
- `clients/*.yaml`
- `views/*.yaml`
- Runtime state records

### 3.5 Reconciler mechanics

Source: ChatGPT #17, Claude S7

- Trigger: startup, periodic, config-change-driven, or all?
- Push-based or poll-based?
- Partial convergence retry strategy
- Global or per-subtree reconciliation?
- How are conflicts surfaced to operators?
- Do reconciliation actions emit events?

### 3.6 Versioning and migration

Source: Claude S6, ChatGPT #2

- Module type version semantics (semver?)
- Can two versions coexist?
- Config migration hooks
- Version mismatch handling

### 3.7 Document authority and freeze rules

Source: ChatGPT #20

- Which docs are authoritative vs supporting research?
- What constitutes a frozen decision?
- How is a frozen decision reopened?
- Whether schema changes require version bumps

---

## Scorecard

| Tier | Items | Purpose |
|------|-------|---------|
| 1 | 10 | Blocks writing code |
| 2 | 8 | Blocks production/safety |
| 3 | 7 | Blocks long-term governance |
| **Total** | **25** | |

---

## Suggested next documents

Based on clustering these gaps, the next architecture docs should be:

1. `module-type-system.md` — covers 1.1, 3.6
2. `reference-grammar.md` — covers 1.3
3. `module-node-resource-model.md` — covers 1.4
4. `event-bus-contract.md` — covers 1.5
5. `settings-model.md` — covers 1.7, 3.1, 3.2
6. `runtime-storage-contract.md` — covers 1.9
7. `policy-language.md` — covers 2.1
8. `reconciler-contract.md` — covers 3.5

---

*This document replaces `spine-remaining-gaps.md` and `spine-missing-points.md`
as the canonical gap tracker. Those files remain for attribution.*
