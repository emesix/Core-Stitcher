# VOS-Workbench — Remaining Gaps After Spine Definition

**Status:** Superseded by `canonical-gaps.md`. Retained for attribution.

*Produced by Claude after reviewing core-thesis.md, spine-open-questions.md,
and spine-definition.md. This is the inverse document: what is still NOT
addressed.*

---

## Spine gaps

### S1. Module type registry

We defined module **instances** (UUID, config, wiring). We did not define
module **types**.

- What IS a `core.router`? Where is its code?
- Where do module type definitions live? A Python package? A plugin directory?
- How does the runtime discover and load module types?
- Is there a type manifest (name, version, config schema, entry point)?
- Can third-party module types be installed?

Without this, `type: core.router` in a module.yaml is a string that points
at nothing.

### S2. Bootstrap sequence

Modules have dependencies (`depends_on`). The runtime needs a startup order.

- What starts first?
- What happens with circular dependencies?
- Is there a dependency resolution algorithm (topological sort)?
- What if a dependency fails to start? Does the dependent wait, degrade, or fail?
- Is there a startup timeout per module?

### S3. Event bus contract

The spine definition says `events: pubsub`. That is a one-word answer to a
multi-part question.

Still undefined:

- Subscription mechanism — how does a module subscribe to events?
- Delivery guarantees — at-least-once? at-most-once? exactly-once?
- Ordering — per-source ordered? globally ordered? unordered?
- Durability — are events persisted? How long? Is replay possible?
- Filtering — can a subscriber filter by event type, source module, tags?
- Correlation — do events carry a causality chain (parent event ID)?
- Backpressure — what happens when a subscriber is slow?
- Scope — per-project events? global events? both?

### S4. API contract for frontends

The thesis says frontends connect via API. Nothing defines that API.

- Protocol — REST? WebSocket? gRPC? All three?
- Authentication — how does a frontend prove identity?
- Authorization — can different frontends have different permissions?
- Streaming — how does the frontend get live updates (events, task progress)?
- Session model — does a frontend session map to a runtime session?

### S5. Error propagation model

When a module fails:

- How does the runtime know? Health checks? Exception bubbling? Timeout?
- What happens to modules that depend on the failed module?
- Does the runtime attempt restart? How many times?
- Is there a supervision strategy (like Erlang's one-for-one, one-for-all)?
- How are errors surfaced to frontends?
- How are errors surfaced to the pre-planner (for ephemeral agent failures)?

### S6. Module versioning

The module contract schema has a `version` field. But:

- What does the version mean? Semver? Sequential?
- Can two versions of the same module type coexist?
- What happens when a module type is upgraded?
- Are there migration hooks for config schema changes?
- How does the runtime handle version mismatches between type and instance?

### S7. Reconciler loop

We defined desired/actual/effective states and convergence statuses. We did
not define the reconciler itself.

- When does reconciliation run? On startup? Periodically? On config change?
- Is it pull-based (reconciler polls) or push-based (config change triggers it)?
- What is the reconciliation algorithm?
- How are conflicts resolved (two changes to the same module)?
- Is there a dry-run mode for reconciliation?
- How is reconciliation progress reported?

### S8. Modules vs nodes vs resources — the identity question

The existing repo has three overlapping schemas:

- `node.schema.json` — types: project, container, file, task, terminal,
  resource, memory, session, log, artifact, agent
- `module-contract.schema.json` — module_id, version, capabilities, events
- Module instance contract (spine-definition.md) — uuid, type, config, wiring

Are these three things the same concept? Different layers? Do nodes contain
modules? Do modules produce nodes? This is still fuzzy.

### S9. Concurrency model

Multiple ephemeral agents run in parallel. The runtime mediates direct calls.
Events are pubsub.

But:

- Is the runtime single-process multi-coroutine (asyncio)?
- Or multi-process (subprocess per agent)?
- Or multi-thread?
- How is shared state protected?
- Can modules block the event loop? What prevents that?
- Is there an isolation boundary between modules (separate processes,
  containers, or just async tasks)?

### S10. Graceful shutdown

- What happens when the backend receives SIGTERM?
- Do running agents get time to finish? How much?
- Are ephemeral modules force-killed or drained?
- Is runtime state checkpointed on shutdown?
- What state survives a restart vs what is lost?

---

## Settings gaps

### C1. Config validation lifecycle

- When is config validated? At file load? At module instantiation? Both?
- What happens when validation fails? Module refuses to start? Warning?
- Can a module start with partial/degraded config?
- Where are validation errors reported?

### C2. Config hot-reload

- Can config change while the system is running?
- If yes, which layers support hot-reload? (Probably not bootstrap.)
- How does a module learn its config changed?
- Is there a config change event on the event bus?
- Can a module reject a config change?

### C3. Default values

- Where do default config values come from?
- From the module type definition? Hardcoded in code? A defaults file?
- Are defaults applied before or after precedence merging?

### C4. Config inheritance between instances

- Can module instances inherit from a base config?
- Example: 5 SSH modules that share most settings but differ in host/key.
  Do you duplicate all config, or inherit from a template?
- If inheritance exists, how deep can it go?

### C5. Resources vs modules

The tree has both `resources/` and `modules/`. The distinction is not defined.

- Is a resource something external the system connects TO (Proxmox, OPNsense)?
- Is a module something internal the system runs AS (router, policy engine)?
- Can a module create resources? Can a resource become a module?
- Why are resources not just modules of type `resource.*`?

### C6. Views and clients

The tree has `clients/` and `views/`. Neither is defined.

- What is a client config? Connection settings? Permissions? Layout?
- What is a view? A UI layout preset? A data filter?
- Are these relevant to the backend at all, or purely frontend config
  that happens to live in the tree?

### C7. Multi-project support

- Can one backend instance serve multiple projects?
- If yes, how are projects isolated? Separate module trees? Shared modules?
- Does each project get its own event bus? Own database?
- Or is this explicitly single-project for now?

### C8. Logging and observability config

Bootstrap mentions "logging backend" but nothing defines:

- Log format (structured JSON? text?)
- Log levels per module
- Log routing (file? stdout? external service?)
- Metrics — are module-level metrics exposed?
- Tracing — distributed tracing across module calls?

### C9. The `module://` and `secret://` URI schemes

These appear in examples but are not formally defined.

- What is the full syntax?
- What schemes exist? `module://`, `secret://`, `system://`, `capability://`
- How are they resolved at runtime?
- Are they validated at config load time or lazily at first use?
- What happens when a URI can't be resolved?

---

## Summary: top 10 most critical remaining gaps

| # | Gap | Why it blocks progress |
|---|-----|----------------------|
| 1 | **Module type registry** (S1) | Can't load modules without knowing where types live |
| 2 | **Bootstrap sequence** (S2) | Can't start the system without a startup order |
| 3 | **Event bus contract** (S3) | "pubsub" is not a spec — modules can't subscribe without a contract |
| 4 | **API contract** (S4) | No frontend can connect without a defined API |
| 5 | **Modules vs nodes vs resources** (S8) | Three overlapping identity models cause confusion |
| 6 | **Concurrency model** (S9) | Can't run parallel agents without knowing the execution model |
| 7 | **Config validation lifecycle** (C1) | Can't load config without knowing when/how to validate |
| 8 | **Resources vs modules** (C5) | The tree has both but the distinction is undefined |
| 9 | **URI scheme definitions** (C9) | `module://` appears everywhere but has no formal spec |
| 10 | **Error propagation** (S5) | Can't build resilient systems without a failure model |

---

*This document should shrink as decisions are made. Each resolved gap should
be recorded in spine-definition.md or its own architecture document.*
