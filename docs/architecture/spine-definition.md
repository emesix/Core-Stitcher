# VOS-Workbench — Spine Definition

*Draft specification produced by ChatGPT, reviewed and annotated by Claude.
Fills in the open questions from spine-open-questions.md with concrete decisions.*

**Status:** Superseded by `alpha-proposals.md` for alpha contracts.
Retained as design history. Some decisions here (e.g. separate `resources/`
directory) have been revised — the alpha proposals are authoritative.

---

## 1. Two trees, not one

Do not force one tree to serve both configuration and runtime.

### Config tree

Persistent, versioned, Git-backed, human-editable.

Contains:

- Project identity
- Module instances
- Resource declarations
- Policy rules
- Client/view defaults
- Desired-state settings

### Runtime tree

Live, generated, not the source of truth.

Contains:

- Active sessions
- Running tasks
- Ephemeral agents
- Event streams
- Command executions
- Temporary artifacts
- Health/degraded state

---

## 2. Tree format: directory-per-module YAML

### Proposed structure

```text
VOS-Workbench/
├── workbench.yaml              # Root manifest
├── policy/
│   ├── global.yaml
│   └── protected-paths.yaml
├── resources/
│   ├── local-shell.yaml
│   ├── proxmox.yaml
│   └── opnsense.yaml
├── modules/
│   ├── router-main/
│   │   └── module.yaml
│   ├── policy-main/
│   │   └── module.yaml
│   ├── memory-main/
│   │   └── module.yaml
│   ├── exec-local-shell/
│   │   └── module.yaml
│   └── model-claude/
│       └── module.yaml
├── clients/
│   └── tui.yaml
└── views/
    └── default-layout.yaml
```

Why this format:

- Human readable
- Git diffs stay small
- Concurrent edits are easier
- Module instances stay isolated
- Machine-writing is still easy

---

## 3. Settings precedence

One hard rule:

```
managed policy > bootstrap > project > machine-local override > session/runtime
```

- Higher layer always wins
- Lower layer may refine, not break upward constraints
- Runtime override can change behavior temporarily, but not escape policy

### What belongs where

**Managed policy** — organizational or hard safety constraints:

- Protected paths
- Forbidden tools
- Allowed provider families
- Outbound restrictions

**Bootstrap** — machine/runtime startup settings:

- Database DSN
- Event bus backend
- State directory
- Secret provider
- API listen socket
- Logging backend

**Project config** — what this project wants:

- Enabled modules
- Module instances
- Default model routing
- Project resources
- Client layout defaults
- Memory profile

**Machine-local override** — specific to one workstation or host:

- Local filesystem paths
- Local shell executable
- Personal API endpoint aliases
- Local-only secret refs

**Session/runtime override** — temporary operator choices:

- Current model
- Debug level
- Focused task
- Temporary context budget
- Temporary dry-run mode

---

## 4. Module instance contract

```yaml
uuid: 2db742d5-5f23-4ce0-9c83-7d4dbf18e2c3
name: router-main
type: core.router
lifecycle: persistent
enabled: true

config:
  mode: planning
  max_parallel_agents: 4
  default_model: model://model-claude
  policy: module://policy-main
  memory: module://memory-main
  event_bus: system://eventbus

wiring:
  depends_on:
    - module://policy-main
    - module://memory-main
    - module://exec-local-shell
    - module://model-claude
  provides:
    - capability://routing
    - capability://task-planning

visibility:
  can_see:
    - module://policy-main
    - module://memory-main
    - module://exec-local-shell
    - module://model-claude
```

---

## 5. Wiring resolution

### Default: explicit references

```yaml
policy: module://policy-main
memory: module://memory-main
```

### Optional: selector-based resolution for pools

```yaml
model_selector:
  type: model.chat
  tags: [fast, cheap]
```

Low magic where correctness matters. Flexibility where pooling matters.

---

## 6. Communication model: mixed

### Direct calls — for request/response

- Execute tool
- Read config
- Resolve dependency
- Fetch memory slice

### Event bus — for observation and loose coupling

- Task started / failed / completed
- Module degraded
- Memory promoted
- Config changed

### Rule

Modules do not talk to each other arbitrarily. They communicate through:

- Runtime-mediated direct calls
- Published events

No module-to-module direct calls. This prevents spaghetti.

---

## 7. Runtime state location

| State type | Storage | Rationale |
|------------|---------|-----------|
| Desired state | Git-backed YAML files | Versioned, diffable, portable |
| Durable runtime state | SQLite (→ Postgres later) | Tasks, sessions, module health, event index, memory metadata, reconciliation state |
| Ephemeral runtime state | Process memory | Live agent state, queues, in-flight requests |
| Artifacts | Filesystem | Logs, transcripts, temporary outputs, reports, command captures |

> **Claude's note:** SQLite for the concept phase. Single file, zero
> infrastructure, same SQL schema. Graduate to Postgres when multi-host
> access is actually needed.

---

## 8. Ephemeral module lifecycle

### Rules

Ephemeral modules:

- Are spawned by a persistent router/coordinator
- Get a UUID
- Get a parent task/session ID
- Get a TTL or completion condition
- Get a budget (token limit, time limit, or both)
- Never become part of desired state
- Do appear in runtime state while alive
- Must emit a final result or failure record before cleanup

> **Claude's note:** Budget inheritance prevents runaway agents from burning
> API credits. Claude Code does this with task_budget — one of their better
> safety patterns.

### Lifecycle states

```
created → scheduled → running → completed | failed | cancelled → archived
```

### Archive rule

When an ephemeral worker dies, its:

- Result summary
- Logs
- Artifacts
- Event chain

...stay behind in runtime history. The worker disappears, but its footprint
remains.

---

## 9. Policy rule syntax

```yaml
rules:
  - id: deny-protected-paths
    priority: 100
    match:
      module_type: exec.shell
      action: write
      path_glob:
        - "**/.git/**"
        - "**/.env"
        - "**/.claude/**"
    effect: deny

  - id: ask-remote-exec
    priority: 50
    match:
      module_type: exec.ssh
      action: command
    effect: ask

  - id: allow-safe-read
    priority: 10
    match:
      module_type: exec.shell
      action: read
    effect: allow
```

### Decision order

- Highest priority first
- First match wins
- If no match: default mode decides
- Hard-deny always overrides lower allow

---

## 10. Secrets handling

### Rule

Project config stores **secret references only**, never raw secrets.

```yaml
providers:
  anthropic:
    api_key: secret://env/ANTHROPIC_API_KEY
  openai:
    api_key: secret://pass/openai-api-key
```

### Supported secret providers

- `secret://env/...` — environment variable
- `secret://file/...` — file on disk
- `secret://pass/...` — password store (pass, gopass)
- `secret://vault/...` — Hashicorp Vault or similar

### Export rule

Tree snapshots and Git commits must never resolve secrets into plaintext.

---

## 11. Desired vs actual vs effective state

### Three-state model

- **Desired** — what the config tree says should exist
- **Actual** — what the runtime currently observes
- **Effective** — what remains after precedence, policy, and resolution

### Convergence statuses

- `converged` — desired matches actual
- `pending` — change in flight
- `degraded` — partially converged
- `drifted` — actual diverged from desired without a change request
- `failed` — reconciler gave up

---

## 12. Canonical root objects

### Config roots

- `project`
- `modules`
- `resources`
- `policies`
- `clients`
- `views`

### Runtime roots

- `sessions`
- `tasks`
- `workers`
- `events`
- `artifacts`
- `health`

---

## 13. Root manifest: workbench.yaml

```yaml
project:
  id: vos-workbench
  name: VOS Workbench
  version: 1

settings:
  precedence:
    - managed
    - bootstrap
    - project
    - local
    - runtime

state:
  desired: git
  durable_runtime: sqlite
  ephemeral_runtime: memory
  artifacts: filesystem

roots:
  config:
    - modules
    - resources
    - policies
    - clients
    - views
  runtime:
    - sessions
    - tasks
    - workers
    - events
    - artifacts
    - health

communication:
  direct_calls: runtime-mediated
  events: pubsub
  module_to_module_direct: false

wiring:
  default_mode: explicit
  selector_mode: optional

ephemeral_modules:
  visible_in_runtime: true
  persisted_in_desired_tree: false
  require_parent_task: true
  require_budget: true
  archive_on_exit: true
```

---

## Frozen decisions

These should be treated as locked unless forced to change:

1. Directory-per-module YAML tree
2. Config tree separate from runtime tree
3. Settings precedence: managed > bootstrap > project > local > runtime
4. Explicit wiring by default, selectors optional
5. Mixed communication: runtime-mediated direct calls + event bus
6. SQLite for durable runtime state (Postgres later)
7. Secret refs only, never plaintext
8. Policy rules with priority + first-match-wins
9. Desired / actual / effective state split
10. Ephemeral modules require parent task + budget

---

*This document captures draft decisions. Each should be validated against
implementation reality and updated as needed.*
