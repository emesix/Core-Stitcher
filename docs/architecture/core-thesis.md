# VOS-Workbench — Core Thesis

## What it is

VOS-Workbench is a **modular, headless agentic backend**. It borrows proven
patterns from Claude Code and other open-source agent runtimes (agent loop,
tool execution, context management, permissions, compaction) but does not
reimplement them — it wraps them as configurable, multi-instance modules
identified by UUID. The system topology is defined entirely by its module tree.

Frontends (TUI, GUI, WebUI) connect via API and are a separate concern.
Speed and reliability live in the backend.

## What it is NOT

- Not a chat application with tools bolted on.
- Not a visual workflow builder (N8N-style). No brittle node graphs.
- Not a framework you run inside. It's a **system you configure and deploy**.
- Not tied to a single LLM provider.

## The three pillars

### 1. Module system

Every component is a module instance. Every instance has:

- A **UUID** — unique identity, used as the key for config, wiring, and lifecycle.
- A **type** — what kind of module it is (`core.router`, `exec.ssh`, `memory.file`, etc.).
- A **config** — instance-specific settings, validated against the module type's schema.
- A **lifecycle** — persistent (lives in the tree, always running) or ephemeral (spawned for a task, destroyed after).

The same module type can be instantiated many times with different configs.
Two SSH modules pointing at different hosts. Three routers with different models.
A pool of coding agents spawned on demand. All tracked by UUID, all independently
configured.

### 2. Wiring

Modules need to find and talk to each other. The wiring defines:

- Which modules a given module can **see** (scope/visibility).
- How modules **communicate** (message passing, events, direct calls — TBD).
- How the system **resolves dependencies** (module A needs "an exec.ssh" — which instance?).

The wiring is what makes the tree a system rather than a bag of parts.

### 3. Tree

The config format IS the system definition. One structure defines:

- What modules exist (type + UUID).
- How each is configured.
- How they are wired together.
- What the system topology looks like.

Serializing the tree = snapshotting the system. Diffing two trees = seeing what
changed. Sharing a tree = reproducing a setup.

## Borrowed, not reinvented

The following patterns are proven and should be adapted from reference
implementations, not built from scratch:

| Pattern | Primary reference | Wrap as |
|---------|-------------------|---------|
| Agent loop (think → act → observe → repeat) | Claude Code, OpenHands | `core.router` module |
| Tool execution and dispatch | Claude Code, Goose | `exec.*` modules |
| Context budgeting and compaction | Claude Code | Built into `core.router` |
| Permission engine (deny → ask → allow) | Claude Code | `core.policy` module or router config |
| MCP tool gateway | MCP Python SDK, Goose | `integration.mcp` module |
| Memory (session, working, long-term) | Claude Code auto-memory | `memory.*` modules |
| Event system | OpenHands event stream | Core infrastructure (not a module — the bus modules talk over) |

## Multi-agent orchestration

The end-goal architecture supports dynamic, parallel multi-agent workflows:

```
Request → Pre-planner (router module)
              │
              ├─→ Coding agent (ephemeral, own UUID, own context)
              ├─→ Tester agent (ephemeral)           } all parallel
              ├─→ Documentation agent (ephemeral)
              │
              ← fan-in, merge results
              │
          Pre-planner evaluates
              │
              ├─→ good enough → output
              └─→ not done → loop, spawn more agents
```

Each spawned agent is a real module instance — UUID, own model config, own tool
access, own context window. If one fails, the others keep running. The
pre-planner decides what to do about failures.

This is the end goal. The architecture should support it from day one, but the
first implementation only needs a few modules to prove the spine works.

## Technology

- **Language:** Python (async, FastAPI for API layer, Pydantic for schemas)
- **Why:** The workload is I/O-bound (LLM API calls, SSH, subprocess execution).
  Python's "slowness" is irrelevant here. The bottleneck is always waiting on
  external systems, not CPU.
- **Future TUI:** Textual (Python)

## Open questions

These are deliberately left open for the design phase:

1. **Tree format** — YAML? TOML? JSON? Directory-per-module? Single file?
   Trade-offs: human readability, git diffability, concurrent access.

2. **Module communication** — Message bus? Direct async calls? Event stream?
   Actor model (Erlang-style mailboxes)? Some combination?

3. **Wiring resolution** — Explicit (module A lists UUIDs it talks to) vs.
   declarative (module A says "I need an exec.ssh" and the runtime resolves)?
   Or both?

4. **Ephemeral module lifecycle** — Who spawns them? Who cleans them up? Do they
   persist results somewhere before dying? How does the tree represent
   something that existed briefly?

5. **Provider selection** — When multiple LLM providers are available, how does
   the system pick the right one for a task? Is this a dedicated module or
   a capability of the router?

6. **State persistence** — Where does runtime state live between restarts?
   The tree is config (desired state), but what about session history,
   task progress, memory contents?

---

*Seed document. To be reviewed, challenged, and evolved.*
