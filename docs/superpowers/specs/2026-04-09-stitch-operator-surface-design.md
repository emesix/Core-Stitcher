# Stitch Operator Surface Architecture

> **Stitch is a multi-client operator platform with one shared command and state model; all clients are views over the same control surface, not separate products.**

**Date:** 2026-04-09
**Status:** Approved for implementation
**Scope:** Core platform + UX contract + CLI (detailed) + TUI (detailed) + thin profiles for remaining clients

---

## Table of Contents

1. [North Star](#1-north-star)
2. [System Layers](#2-system-layers)
3. [Core Architecture](#3-core-architecture)
4. [Cross-Client UX Contract](#4-cross-client-ux-contract)
5. [Command Vocabulary](#5-command-vocabulary)
6. [Client Spec: CLI](#6-client-spec-cli)
7. [Client Spec: TUI](#7-client-spec-tui)
8. [Target Profiles](#8-target-profiles)
9. [Phasing](#9-phasing)
10. [Dependency Rules](#10-dependency-rules)
11. [Out of Scope for v1](#11-out-of-scope-for-v1)
12. [Golden Flows](#12-golden-flows)
13. [Glossary](#appendix-a-glossary)

---

## 1. North Star

**One operator model, five clients, shared command/state/event language.**

Stitch exposes a single coherent operator experience across CLI, TUI, minimal HTML, full WebUI, and desktop. Every client can: open a resource, inspect a node, run preflight, trace a VLAN path, view impact, orchestrate a task, watch logs, accept/reject AI suggestions, and commit changes.

### What is shared across all clients

- Domain models (Device, Port, Link, VLAN, Run, Task, Review...)
- API client + stream client
- Command vocabulary (`stitch device show`, `stitch preflight run`, ...)
- Resource identity scheme (`stitch:/device/dev_01HX`)
- State machine (run lifecycle, review workflow)
- Permissions model
- Result schemas
- Error model

### What is NOT shared

- Pixel-level widgets or rendering
- Layout systems
- Platform-specific keybindings (beyond a common baseline)
- Navigation chrome
- Presentation-specific interaction patterns

The domain layer (existing stitch.* packages) models topology. The operator layer models how a human interacts with that topology. These are architecturally separate concerns.

---

## 2. System Layers

```
+-------------------------------------------------------------+
|                       CLIENT LAYER                           |
|  stitch-cli  stitch-tui  stitch-lite  stitch-web  stitch-desktop |
+-----------------------------+-------------------------------+
                              | uses
+-----------------------------+-------------------------------+
|                      OPERATOR LAYER (new)                    |
|                                                              |
|  stitch-core               |  stitch-sdk                    |
|  ----------                |  ----------                    |
|  Command model             |  Typed API client              |
|  Query model               |  Stream client (WS/SSE)        |
|  Stream model              |  Auth / session                |
|  Resource identity         |  Helpers / formatters          |
|  UX contract types         |                                |
|  Capability discovery      |                                |
+-----------------------------+-------------------------------+
                              | calls
+-----------------------------+-------------------------------+
|                DOMAIN LAYER (exists, rename pending)          |
|                                                              |
|  stitch_workbench (spine)  |  stitch.* namespace            |
|  ----------------------    |  -----------------             |
|  Runtime, config,          |  contractkit (protocols)       |
|  events, storage,          |  modelkit (domain types)       |
|  module registry,          |  graphkit, storekit            |
|  FastAPI bootstrap         |  adapters (switchcraft..)      |
|                            |  engines (verifykit..)         |
|                            |  interfacekit (HTTP)           |
|                            |  agentcore (orchestration)     |
+-------------------------------------------------------------+
```

### Key boundary

The operator layer imports from modelkit/contractkit for domain types, but never from spine internals. It talks to the domain layer through the existing FastAPI API surface. Clients only import from stitch-core and stitch-sdk — never from stitch.* directly.

### Package mapping

| Package | Language | Contains |
|---|---|---|
| `stitch-core` | Python | Command/Query/Stream models, Resource URIs, UX contract types, capability registry |
| `stitch-sdk` | Python | API client, WebSocket/SSE stream client, auth, session management |
| `stitch-cli` | Python (Typer) | CLI commands, output formatters (human/json/table) |
| `stitch-tui` | Python (Textual) | Terminal UI screens, widgets, keybindings |
| `stitch-lite` | Python (Jinja2) | Server-rendered HTML templates, minimal JS |
| `stitch-web` | TypeScript (React) | Full WebUI SPA |
| `stitch-desktop` | Rust+TS (Tauri) | Desktop shell wrapping stitch-web + native integrations |

---

## 3. Core Architecture

### 3.1 Resource Identity

Every addressable thing in Stitch has a URI. This is the deep-link, navigation, and piping primitive that all clients share.

```
stitch:/{resource_type}/{canonical_id}[/{sub_resource}/{sub_id}]
```

Single-slash, no fake host semantics.

```
stitch:/device/dev_01HXYZ
stitch:/device/dev_01HXYZ/port/port_0A
stitch:/link/lnk_7KM2
stitch:/vlan/42
stitch:/topology/current
stitch:/topology/snap_20260409T120000
stitch:/report/rpt_a1b2c3d4
stitch:/run/run_18f2a3b1
stitch:/run/run_18f2a3b1/task/tsk_003F
stitch:/run/run_18f2a3b1/task/tsk_003F/step/stp_007Q
stitch:/run/run_18f2a3b1/review/rev_001A
stitch:/module/switchcraft
```

**Rules:**

- Canonical IDs are stable and opaque (prefixed type hints: `dev_`, `lnk_`, `rpt_`, `run_`, `tsk_`, `stp_`, `rev_`)
- Friendly names (`sw-core-01`) are aliases, resolved via lookup — never the canonical ID
- CLI accepts both: `stitch device show sw-core-01` resolves the alias, `stitch show stitch:/device/dev_01HXYZ` uses the URI directly
- Renames change the alias, never the canonical ID
- Every canonical URI resolves to one canonical resource identity and one declared schema family, with optional sparse fieldsets and version-compatible projections

### 3.2 Command Model

Commands are actions that change state. Every mutation goes through a command, not ad-hoc API calls.

```python
@dataclass
class Command:
    action: str                  # structured: "preflight.run", "trace.run"
    target: str | None           # stitch URI (None for system-level commands)
    params: dict[str, Any]       # action-specific parameters
    source: CommandSource        # which client issued it
    correlation_id: str          # for tracing
    idempotency_key: str | None  # prevents double-submits

class CommandSource(StrEnum):
    CLI = "cli"
    TUI = "tui"
    WEB = "web"
    LITE = "lite"
    DESKTOP = "desktop"
    API = "api"                  # direct API call
    SCRIPT = "script"            # non-interactive CLI / automation
    INTERNAL = "internal"        # system-initiated
```

**Naming convention:** `target` for input (what you're acting on), `resource` for output (what was affected).

**Action names are structured, not free-form:**

```
preflight.run
trace.run
impact.preview
run.create
run.execute
run.cancel
review.request
review.approve
review.reject
topology.export
topology.diff
module.restart
```

Pattern: `{domain}.{noun}.{verb}` or `{domain}.{verb}` when the noun is implicit.

**Command registry** — each action is registered with:

```python
@dataclass
class CommandSpec:
    action: str
    target_types: list[str]
    params: list[ParamSpec]
    required_capabilities: list[str]
    default_mode: ExecutionMode
    returns: str                       # resource type or result schema name
    creates_run: bool
    supports_cancel: bool
    interaction: InteractionClass
    risk: RiskLevel
    description: str

class InteractionClass(StrEnum):
    NONE = "none"           # fire and forget
    CONFIRM = "confirm"     # yes/no gate
    FORM = "form"           # requires parameter input
    WIZARD = "wizard"       # multi-step guided flow

class RiskLevel(StrEnum):
    LOW = "low"             # read-like or reversible
    MEDIUM = "medium"       # state change, recoverable
    HIGH = "high"           # destructive or hard to reverse
```

### 3.2.1 Command Execution Semantics

```python
class ExecutionMode(StrEnum):
    SYNC = "sync"       # returns result directly
    ASYNC = "async"     # returns run/task handle, watch for completion
```

| Action | Default mode | Returns | Creates run |
|---|---|---|---|
| `device.inspect` | sync | DeviceDetail | no |
| `preflight.run` | async | RunHandle | yes |
| `trace.run` | sync | TraceResult | no |
| `impact.preview` | sync | ImpactResult | no |
| `run.execute` | async | RunHandle | yes (continues existing) |
| `review.request` | async | ReviewHandle | yes |
| `review.approve` | sync | ReviewResult | no |
| `review.reject` | sync | ReviewResult | no |
| `run.cancel` | sync | Acknowledgment | no |

**Sync-to-async promotion:** CommandSpec declares `default_mode`. The server may promote a sync-capable action to async for large scopes. The response includes `effective_mode: ExecutionMode` so the client knows what actually happened.

**Client rules:**

- Sync: client waits, displays result
- Async: client receives handle immediately, then polls or subscribes to stream
- CLI async: prints run ID, optionally tails with `--watch`
- TUI async: auto-subscribes to run's stream, updates live

### 3.3 Query Model

Queries are read-only. No presentation concerns — formatting is the client's job.

```python
@dataclass
class Query:
    resource_type: str
    resource_id: str | None      # None = list, Some = get
    filters: list[Filter]
    sort: str | None             # field name, prefix "-" for desc
    limit: int | None
    cursor: str | None           # opaque, from previous page
    fields: list[str] | None    # sparse fieldset

@dataclass
class Filter:
    field: str
    op: FilterOp
    value: str | list[str]

class FilterOp(StrEnum):
    EQ = "="
    NEQ = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    CONTAINS = "~"
    IN = "in"

@dataclass
class QueryResult:
    items: list[dict[str, Any]]  # conform to declared ResourceSpec schema
    total: int | None
    next_cursor: str | None
```

Items conform to the declared ResourceSpec or result schema. Sparse fieldsets may omit fields. Unknown fields must be ignored by clients.

### 3.3.1 Filter Grammar

v1 is intentionally tight. All filters are AND. Multi-value within a filter is OR.

```
stitch device list --filter type=SWITCH
stitch device list --filter severity>=WARNING
stitch device list --filter name~core
stitch device list --filter status=PENDING,RUNNING
stitch device list --filter type=SWITCH --filter name~core
```

v1 operators: `=`, `!=`, `>`, `>=`, `<`, `<=`, `~`, `in`. `=` with comma-separated values (`status=PENDING,RUNNING`) is syntactic sugar for `in` (`status in PENDING,RUNNING`). They are equivalent. Flat field references only. No nested paths. No OR across different fields. No parenthetical grouping. Documented precisely so every client parses identically.

### 3.4 Stream Model

```python
@dataclass
class StreamSubscription:
    topic: StreamTopic
    target: str | None           # stitch URI to scope
    filters: list[Filter]        # same Filter type as Query
    last_event_id: str | None    # for resume after disconnect

class StreamTopic(StrEnum):
    RUN_PROGRESS = "run.progress"
    RUN_LOG = "run.log"
    TASK_STATUS = "task.status"
    REVIEW_VERDICT = "review.verdict"
    MODULE_HEALTH = "module.health"
    TOPOLOGY_CHANGE = "topology.change"
    SYSTEM_EVENT = "system.event"
```

### 3.4.1 Event Envelope and Recovery

```python
@dataclass
class StreamEvent:
    event_id: str                # globally unique
    sequence: int                # monotonic per topic+target
    topic: StreamTopic
    resource: str                # stitch URI of affected resource
    payload: dict[str, Any]
    timestamp: datetime
    correlation_id: str | None
```

**Topic durability:**

| Topic | Durable | Replay window | Notes |
|---|---|---|---|
| `run.progress` | yes | lifetime of run | critical for resume |
| `run.log` | yes | lifetime of run | must survive disconnect |
| `task.status` | yes | lifetime of run | |
| `review.verdict` | yes | lifetime of run | |
| `module.health` | no | last value only | current state, not history |
| `topology.change` | yes | 24h | for detecting missed updates |
| `system.event` | no | none | ephemeral, best-effort |

**Recovery protocol:**

1. Client connects with `last_event_id` from its last received event
2. Server replays missed events from that point (for durable topics)
3. If `last_event_id` is too old or expired, server sends a `reset` event — client must re-fetch full state
4. Non-durable topics: client gets current value on connect, then live updates

**Transport:** WebSocket primary. SSE fallback for minimal HTML client. The SDK wraps transport-level failures (timeout, broken connection, invalid JSON, gateway errors) into `TransportError`. `StitchError` is reserved for server-returned domain/protocol errors. The SDK stream client handles reconnection with exponential backoff and automatic `last_event_id` resume.

### 3.5 Auth & Session

```python
@dataclass
class Session:
    session_id: str
    user: str
    capabilities: set[str]
    scopes: dict[str, list[str]] | None   # capability -> resource constraints
    client: CommandSource
    created_at: datetime
    expires_at: datetime | None
```

**Capabilities:**

```python
class Capability(StrEnum):
    TOPOLOGY_READ = "topology.read"
    PREFLIGHT_RUN = "preflight.run"
    TRACE_RUN = "trace.run"
    IMPACT_RUN = "impact.run"
    RUNS_MANAGE = "runs.manage"
    RUNS_REVIEW = "runs.review"
    CHANGES_APPROVE = "changes.approve"
    LOGS_VIEW = "logs.view"
    ADMIN = "admin"
```

**Scope constraints (v1, simple):**

```python
scopes = {
    "topology.read": ["site=rotterdam"],
    "runs.manage": ["domain=network"],
}
# None means unrestricted for that capability
```

**Rules:**

- All clients authenticate the same way (token from config/env/prompt)
- Capabilities checked at command/query dispatch, not per-client
- CLI and WebUI sessions for the same user have identical permissions
- No client gets special privileges

### 3.6 Capability Discovery

Declarative, not magic. Used for validation and UI assistance, not as a design engine.

```python
@dataclass
class SystemCapabilities:
    commands: list[CommandSpec]
    resource_types: list[ResourceSpec]
    stream_topics: list[StreamTopicSpec]
    version: str

@dataclass
class ResourceSpec:
    type: str
    uri_pattern: str             # "stitch:/device/{id}"
    supports_list: bool
    supports_stream: bool
    fields: list[FieldSpec]
    alias_field: str | None      # which field is the friendly name
```

**Use for:** command palette population, input validation, auth-aware hiding/disabling, form scaffolding, client version compatibility checks.

**Not for:** fully generated UI screens, dynamic layout derivation, replacing intentional client design.

### 3.7 Error Model

Shared across commands, queries, and streams.

```python
@dataclass
class StitchError:
    code: str                    # structured: "device.not_found", "auth.forbidden"
    message: str
    detail: dict[str, Any] | None
    retryable: bool
    correlation_id: str | None
    field_errors: list[FieldError] | None

@dataclass
class FieldError:
    field: str
    code: str
    message: str
```

**Error code patterns:**

- `{resource}.not_found` — 404
- `{resource}.conflict` — 409 (idempotency collision, stale state)
- `auth.forbidden` — 403
- `auth.expired` — 401
- `command.invalid_params` — 400
- `command.not_available` — capability not present or not applicable
- `stream.reset` — client must re-fetch full state
- `system.unavailable` — 503

The SDK wraps transport-level failures (timeout, broken connection, invalid JSON, gateway errors) into `TransportError`, a separate type from `StitchError`.

### 3.8 Lifecycle States

Standard state machine for anything that runs over time.

```
PENDING -> QUEUED -> RUNNING -> SUCCEEDED
                           |-> FAILED
                           |-> CANCELLED
                           |-> TIMED_OUT
```

```python
class LifecycleState(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
```

**Allowed transitions:**

| From | To | Trigger |
|---|---|---|
| PENDING | QUEUED | accepted for scheduling |
| PENDING | CANCELLED | user cancels before scheduling |
| PENDING | FAILED | system failure before queueing |
| QUEUED | RUNNING | executor picks up work |
| QUEUED | CANCELLED | user cancels before execution |
| RUNNING | SUCCEEDED | completes normally |
| RUNNING | FAILED | error during execution |
| RUNNING | CANCELLED | user cancels |
| RUNNING | TIMED_OUT | budget/time exceeded |

Terminal states (SUCCEEDED, FAILED, CANCELLED, TIMED_OUT) are final. All clients display the same state names and transitions. Stream events carry the new state on every transition.

---

## 4. Cross-Client UX Contract

The behavioral language between core protocol and client-specific rendering. Every client implements these concepts in its own idiom, but the semantics are shared.

### 4.1 Resource

A Resource is anything a user can open, inspect, act on, or link to. It is the unit of attention.

```python
@dataclass
class Resource:
    uri: str                     # stitch:/device/dev_01HXYZ
    type: str                    # "device", "run", "vlan", etc.
    display_name: str            # "sw-core-01" (alias)
    summary: str                 # one-line description
    status: LifecycleState | None
    parent: str | None           # parent URI
    children_hint: int | None    # count of sub-resources
```

**Resource is a navigable summary.** Detailed fields come from panel queries or resource-specific detail schemas. Clients must not expect Resource to carry full domain objects.

### 4.2 Context & Selection

Context is what the user is currently focused on. It scopes queries, commands, and panels.

```python
@dataclass
class Context:
    scope: str | None            # what the user is looking within
    selection: list[str]         # what the user intends to act on
    filters: list[Filter]
    view: str | None             # client-local presentation hint
```

**Scope vs working set:** Scope and selection can differ. Example: scoped to VLAN 42, selected three devices within that scope for batch preflight. Scope narrows what's visible; selection targets what's acted on.

Context is client-local state, not server state. But every client must be able to serialize context to a URI or query string for deep-linking, sharing, and restoring.

### 4.3 Action

An Action is a user-invokable operation, resolved from the command registry for the current context.

```python
@dataclass
class Action:
    command_action: str          # maps to Command.action
    label: str                   # "Run Preflight"
    icon: str | None
    available: bool              # based on capabilities + context
    reason: str | None           # why unavailable
    keyboard_shortcut: str | None
    interaction: InteractionClass
    risk: RiskLevel
```

Given a context (selection, focused resource type), the client asks: "what actions are available here?" Derived from command registry + auth capabilities + resource type — not hardcoded per client.

Client idioms: CLI = subcommands, TUI = command palette + context menu, WebUI = toolbar + right-click + palette.

### 4.4 Panel

A Panel is a structured view definition — semantic content, not pixel layout.

```python
@dataclass
class PanelSpec:
    id: str                      # "device.detail", "run.progress"
    title: str
    resource_types: list[str]
    sections: list[PanelSection]
    refresh: RefreshPolicy

@dataclass
class PanelSection:
    id: str
    title: str
    kind: SectionKind
    data_source: str             # named data source ID, e.g. "device.ports"
    stream_topic: StreamTopic | None

class SectionKind(StrEnum):
    FIELDS = "fields"            # key-value detail view
    TABLE = "table"              # tabular list
    LOG = "log"                  # streaming text
    STATUS = "status"            # lifecycle + progress
    GRAPH = "graph"              # topology visualization
    DIFF = "diff"                # side-by-side comparison
```

Sections reference named data sources parameterized by current context, not inline Query objects. Resolution is the SDK's job.

Panel specs are a helper, not a mandate. Rich clients may compose panels differently, add client-specific sections, or skip sections their medium cannot render. Unsupported SectionKinds degrade gracefully: skip, fall back to table/list, or show an unsupported notice.

### 4.5 Run / Job / Task

```python
@dataclass
class RunView:
    uri: str
    status: LifecycleState
    description: str
    progress: Progress | None
    tasks: list[TaskView]
    active_task: str | None      # stitch URI of currently executing task
    requires_attention: bool
    attention_reason: str | None

@dataclass
class Progress:
    completed: int
    total: int
    percent: float
    elapsed: timedelta
    estimated_remaining: timedelta | None

@dataclass
class TaskView:
    uri: str
    status: LifecycleState
    description: str
    domain: str
    executor: str | None
    outcome_summary: str | None
```

When `requires_attention=True`, all clients surface it prominently.

### 4.6 Notification & Live Event

**Hybrid persistence model:**

- `ACTION_REQUIRED` and `ERROR` notifications are server-issued and persisted — read/dismissed state syncs across clients
- `INFO` and `WARNING` notifications are ephemeral — derived client-side from stream events, no cross-client sync

```python
@dataclass
class Notification:
    id: str
    severity: NotificationSeverity
    title: str
    body: str | None
    resource: str
    action_hint: str | None
    timestamp: datetime
    read: bool
    dismissed: bool

class NotificationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    ACTION_REQUIRED = "action_required"
```

Server-persisted notifications are queryable via `stitch notification list`.

### 4.7 Review / Diff / Approval

```python
class ReviewVerdict(StrEnum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    REJECT = "reject"

@dataclass
class ReviewView:
    uri: str
    status: LifecycleState       # PENDING = awaiting verdict, SUCCEEDED = completed (not necessarily approved)
    run: str
    verdict: ReviewVerdict | None
    findings: list[FindingView]
    summary: str | None
    reviewer: str                # "ai" or user identity
    requires_human: bool

@dataclass
class FindingView:
    description: str
    severity: str
    resource: str | None
    suggestion: str | None
    category: str | None

@dataclass
class DiffView:
    before: str
    after: str
    sections: list[DiffSection]

@dataclass
class DiffSection:
    title: str
    kind: str                    # "added", "removed", "changed", "unchanged"
    items: list[dict[str, Any]]
```

**Core rule: AI can suggest, never silently mutate.** Every AI-generated review or suggestion requires explicit approval. The approval workflow is identical regardless of whether the review came from AI or a human.

**Audit trail:** Every approve/reject action records: actor, timestamp, target URI, verdict, basis (findings summary), and correlation_id. Persisted server-side and queryable.

---

## 5. Command Vocabulary

### Namespace types

| Type | Names | Meaning |
|---|---|---|
| Resource namespace | device, port, link, vlan, topology, report, run, task, step, review, notification, module, config | Maps 1:1 to a resource type, supports show/list |
| Hybrid namespace | trace, impact | Workflow entry points that also produce stored results (show/list supported) |
| Workflow namespace | preflight, ai, search | Entry points for domain workflows, may create resources |
| System namespace | system | System-level queries, no backing resource |

Trace and impact results are stored and addressable (`stitch:/trace/trc_XXXX`, `stitch:/impact/imp_XXXX`). They are workflow-initiated but resource-backed.

### Resource types and their verbs

```
RESOURCE        VERBS                           NOTES
---------------------------------------------------------------
device          show, list, inspect             inspect = detail + ports + neighbors
port            show, list                      always scoped to device
link            show, list, inspect             inspect = endpoints + checks
vlan            show, list                      show includes member ports
topology        show, export, diff, diagnostics show = summary, export = full snapshot
report          show, list, diff                generic: preflight, audit, etc.
trace           run, show, list                 VLAN path tracing
impact          preview, show, list             change impact analysis
run             create, show, list, watch,      full orchestration lifecycle
                execute, cancel
task            show, list                      always scoped to run
step            show, list                      always scoped to task
review          request, show, list,            AI or human review
                approve, reject
notification    list, read, dismiss             read marks as read
module          show, list, health              runtime module status
config          show, validate                  system configuration
system          health, info, version           system-level queries
```

### Action name mapping

| CLI command | Action name | Mode | Risk |
|---|---|---|---|
| `stitch device show` | `device.show` | sync | low |
| `stitch device inspect` | `device.inspect` | sync | low |
| `stitch preflight run` | `preflight.run` | async | low |
| `stitch trace run` | `trace.run` | sync | low |
| `stitch impact preview` | `impact.preview` | sync/async | low |
| `stitch topology diff` | `topology.diff` | sync | low |
| `stitch run create` | `run.create` | sync | low |
| `stitch run execute` | `run.execute` | async | medium |
| `stitch run cancel` | `run.cancel` | sync | medium |
| `stitch review request` | `review.request` | async | low |
| `stitch review approve` | `review.approve` | sync | high |
| `stitch review reject` | `review.reject` | sync | medium |
| `stitch ai review` | `ai.review` | async | low |
| `stitch ai suggest` | `ai.suggest` | async | low |
| `stitch topology diagnostics` | `topology.diagnostics` | sync | low |
| `stitch report diff` | `report.diff` | sync | low |
| `stitch search` | `search.run` | sync | low |

**Default rule for unlisted actions:** All `show`, `list`, `inspect`, `health`, `info`, `version`, `diagnostics`, `export`, `validate`, `read`, and `dismiss` actions are sync, low risk, and return their corresponding resource type or result schema. Only actions that deviate from this default (async, medium/high risk, or creating runs) need explicit table entries.

### Piping and composition

```bash
# List switch devices, pipe compact output
stitch device list --filter type=SWITCH --output compact

# Pipe device IDs into batch inspect
stitch device list --filter type=SWITCH --output compact | \
  xargs -I{} stitch device inspect {}

# Run preflight, capture run ID, then watch
RUN_ID=$(stitch preflight run --scope site-rdam --output json | jq -r '.run_id')
stitch run watch "$RUN_ID"

# Export topology, diff against saved baseline
stitch topology export > current.json
stitch topology diff baseline.json current.json

# Batch from stdin
stitch device list --filter type=SWITCH --output compact | \
  stitch preflight run --from-stdin

# JSON for scripting
stitch run list --filter status=FAILED --output json | jq '.items[].uri'
```

---

## 6. Client Spec: CLI

### 6.1 Stack and entry point

```
Package:    stitch-cli
Language:   Python
Framework:  Typer
Depends on: stitch-core, stitch-sdk
Entry:      stitch (console_scripts)
```

### 6.2 Command tree

```
stitch
|-- device
|   |-- show <id|alias>
|   |-- list [--filter ...]
|   +-- inspect <id|alias>
|
|-- port
|   |-- show <id|alias|device port>
|   +-- list --device <id|alias>
|
|-- link
|   |-- show <id>
|   |-- list [--filter ...]
|   +-- inspect <id>
|
|-- vlan
|   |-- show <vlan_id>
|   +-- list [--filter ...]
|
|-- topology
|   |-- show
|   |-- export [--format json|yaml]
|   |-- diff <before> <after>
|   +-- diagnostics
|
|-- preflight
|   +-- run [--scope ...] [--watch]
|
|-- trace
|   |-- run <vlan_id> --from <device> [--to <device>]
|   |-- show <id>
|   +-- list [--filter ...]
|
|-- impact
|   |-- preview --action <action> --device <id> --port <port> [--watch]
|   |-- show <id>
|   +-- list [--filter ...]
|
|-- run
|   |-- create <description> [--domain ...] [--priority ...]
|   |-- show <id>
|   |-- list [--filter ...]
|   |-- watch <id>
|   |-- execute <id>
|   +-- cancel <id> [--reason ...]
|
|-- task
|   |-- show <id>
|   +-- list --run <id> [--filter ...]
|
|-- step
|   |-- show <id>
|   +-- list --task <id> [--filter ...]
|
|-- review
|   |-- request <run_id>
|   |-- show <id>
|   |-- list [--filter ...]
|   |-- approve <id> [--comment ...]
|   +-- reject <id> [--comment ...]
|
|-- report
|   |-- show <id|latest>
|   |-- list [--filter type=preflight]
|   +-- diff <id1> <id2>
|
|-- ai
|   |-- review <run_id>
|   +-- suggest <run_id>
|
|-- notification
|   |-- list [--filter ...]
|   |-- read <id>
|   +-- dismiss <id>
|
|-- module
|   |-- show <name>
|   |-- list
|   +-- health [<module_name>]
|
|-- config
|   |-- show
|   +-- validate [<file>]
|
|-- system
|   |-- health
|   |-- info
|   +-- version
|
|-- search <text> [--type ...] [--limit ...]
|
|-- show <uri>                       # open any resource by stitch URI
|
+-- Global flags:
    --output json|table|compact|yaml|human (default: human)
    --filter <field><op><value>      # repeatable
    --sort <field>                   # prefix - for desc
    --limit <n>
    --target <uri>                   # repeatable, for batch operations
    --from-stdin                     # read target URIs from stdin
    --targets-file <path>            # read targets from file
    --yes                            # skip confirmation
    --non-interactive                # fail instead of prompting
    --no-color
    --quiet
    --verbose
    --pager / --no-pager             # default: auto on TTY
    --config <path>
    --profile <name>
```

### 6.3 Output modes

| Mode | Flag | Use case | Stable contract |
|---|---|---|---|
| human | `-o human` (default on TTY) | Interactive terminal | No (may change between versions) |
| table | `-o table` | Structured lists | No |
| json | `-o json` | Scripting, piping | Yes |
| compact | `-o compact` (default when piped) | Piping to other commands | Yes |
| yaml | `-o yaml` | Config work | Yes |

**Compact output contract:** `uri<TAB>display_name<TAB>status`, one line per resource, TAB-delimited (literal `\t`). First three columns and the TAB delimiter are the stable contract. Additional type-specific fields may be appended after status as extra TAB-separated columns.

**Stdout/stderr discipline:**

- `stdout`: command results only (the data)
- `stderr`: progress bars, watch status, prompts, warnings, confirmation dialogs
- Rule: `stitch device list | jq` must never see progress noise

### 6.4 Streaming and async behavior

Without `--watch`:

```
$ stitch preflight run --scope site-rdam
Run started: run_4f8a2b (preflight)
Use `stitch run watch run_4f8a2b` to follow progress.
```

With `--watch`:

```
$ stitch preflight run --scope site-rdam --watch
Run: run_4f8a2b (preflight)
============================================= 3/16 == 18%
ok tsk_001 collect switchcraft observations
ok tsk_002 collect opnsensecraft observations
.. tsk_003 collect proxmoxcraft observations...
   tsk_004 merge observations
   ...

[Ctrl+C to detach, run continues in background]
```

Rules:

- `--watch` subscribes to the run's stream via stitch-sdk
- Ctrl+C detaches the CLI but does not cancel the run
- Progress uses carriage return / ANSI for in-place updates on TTY
- Non-TTY `--watch` falls back to line-by-line log output

**Watch exit semantics:**

- `0` = watched run SUCCEEDED
- `1` = watched run FAILED / CANCELLED / TIMED_OUT
- `5` = user interrupted (Ctrl+C), run still active

### 6.5 Batch behavior

Default: continue on failure, process all targets. Exit code `1` if any target failed. Summary to stderr: `3 succeeded, 1 failed, 0 skipped`. `--fail-fast` flag to stop on first failure.

### 6.6 Exit codes

```
0    Success
1    Command failed (domain error, action rejected, batch partial failure)
2    Usage error (bad arguments, missing required params)
3    Auth failure (expired, forbidden)
4    Connection failure (server unreachable, timeout)
5    Interrupted (user cancelled with Ctrl+C)
10   Non-interactive mode required confirmation (--non-interactive without --yes)
```

### 6.7 Config and auth

```yaml
# ~/.config/stitch/config.yaml
default_profile: lab

profiles:
  lab:
    server: https://stitch.lab.local:8443
    token_command: "pass show stitch/lab-token"
  prod:
    server: https://stitch.prod.internal:8443
    token_command: "vault read -field=token secret/stitch/prod"

defaults:
  output: human
  color: auto          # auto | always | never
  confirm: true
  page_size: 50
```

**Resolution order:**

- Profile: `--profile` > `STITCH_PROFILE` > `config.default_profile`
- Server: `STITCH_SERVER` > `profile.server`
- Token: `STITCH_TOKEN` > `profile.token_command` > `profile.token`

Token sourcing: `token_command` runs a shell command and reads stdout (supports pass, vault, keyring). No token storage in config by default.

### 6.8 Shell completion

Typer built-in completion for bash/zsh/fish. Additionally:

- Resource ID completion queries aliases via SDK
- Flag value completion shows enum values from capability discovery
- Completion failure fails soft — never blocks shell behavior

---

## 7. Client Spec: TUI

### 7.1 Stack and layout model

```
Package:    stitch-tui
Language:   Python
Framework:  Textual
Depends on: stitch-core, stitch-sdk
Entry:      stitch-tui (console_scripts)
```

**Default 3-zone layout:**

```
+----------------------------------------------------------------+
| TOP BAR: profile @ server  |  scope  |  connection  |  alerts  |
+----------------+-----------------------------------------------+
|  LEFT SIDEBAR  |  CENTER WORKSPACE                             |
|                |                                               |
|  Explorer      |  Active screen: resource detail, run monitor, |
|  Search        |  review, diff, search results, etc.           |
|  Selection     |                                               |
|  Active runs   |                                               |
|  Alerts        |                                               |
+----------------+-----------------------------------------------+
| BOTTOM PANEL: logs | events | steps | notifications            |
+----------------------------------------------------------------+
| FOOTER: key hints                               | mode: browse |
+----------------------------------------------------------------+
```

**Decision:** IDE-inspired 3-zone operator console. Shows navigation + detail + live activity simultaneously. Maps directly to the UX contract. Adopts focus/zoom modes and narrow-terminal fallback from screen-switching approach.

**Important rule:** The TUI is terminal-native, not a fake WebUI. Keyboard-first, fast pane switching, strong palette, compact summaries, graceful degradation.

### 7.2 Panes and responsibilities

| Pane | Content | Resize | Hide |
|---|---|---|---|
| Top bar | Profile, server, scope, connection/staleness, alert badge | No | No |
| Left sidebar | Resource explorer, search results, selection, active run badges, notification count | Width adjustable | Ctrl+E toggle |
| Center workspace | Active screen (one at a time) | Fills remaining | No |
| Bottom panel | Tabbed: Logs, Events, Steps, Notifications | Height adjustable | Ctrl+B toggle |
| Footer | Context-sensitive key hints, current mode | No | No |

Focus: Tab/Shift-Tab cycles between sidebar, center, bottom. Focused pane has visible border highlight. Only focused pane receives keyboard input.

### 7.3 Navigation model

| Action | Key | Behavior |
|---|---|---|
| Open / drill down | Enter | Navigate into selected resource |
| Go back / parent | Backspace or h | Return to parent view |
| Jump to URI | Ctrl+G | Prompt for stitch URI, navigate directly |
| Follow link | Enter on linked resource | Navigate to referenced resource |
| History forward | Ctrl+] | Forward in navigation history |

History: back/forward stack like a browser.

### 7.4 Screen types

| Screen | Trigger | Center content |
|---|---|---|
| Resource list | sidebar selection, command | Filterable table, sortable columns |
| Device detail | Open a device | Info fields + ports table + neighbors |
| Run detail | Open a run | Status, progress, task list, active task |
| Run watch | `w` on a run | Live-updating run detail + auto-scrolling logs |
| Review | Open review or notification | Findings list, detail, approve/reject |
| Diff | `d` on two selected resources | Side-by-side before/after |
| Search results | `/` search or Ctrl+P | Cross-resource results |
| Trace result | After trace command | Hop-by-hop path with status |
| Impact preview | After impact command | Affected resources with severity |
| Topology summary | Topology overview | Device table + links + diagnostics |
| Module health | System health | Module list with status |

### 7.5 Selection and batch operations

| Action | Key | Behavior |
|---|---|---|
| Toggle select | Space | Select/deselect focused resource |
| Select range | Shift+Space | Select from last selected to current |
| Select all visible | Ctrl+A | Select all filtered resources |
| Clear selection | Escape | Clear all |

Selected resources appear in sidebar under "SELECTION" with count. Batch actions apply to working set with confirmation prompt showing count and action.

**High-risk batch guard:** If `risk=HIGH` and selection > 1, require typed confirmation (e.g., "approve 5 reviews? type YES:").

### 7.6 Live update behavior

**Auto-subscriptions:**

| Context | Topics |
|---|---|
| Always | `module.health`, `system.event` |
| Run detail open | `run.progress`, `run.log`, `task.status` scoped to run |
| Watch mode | Same + auto-scroll logs |
| Review pending | `review.verdict` scoped to run |

**Bottom panel tabs:**

| Tab | Source |
|---|---|
| Logs | `run.log` stream + historical query |
| Events | `system.event`, `topology.change` |
| Steps | `run.progress` stream |
| Notifications | Query + persisted notifications |

Unread markers on non-focused tabs. Buffer last 1000 lines per tab. Scroll up pauses auto-scroll; `G` or `End` resumes.

**Stream staleness indicators:** Connected | Reconnecting (with backoff timer) | Stale (>30s no heartbeat) | Replaying (catching up, shows count). Shown prominently in top bar during watch mode.

### 7.7 Keybindings

**Global:**

| Key | Action |
|---|---|
| Tab / Shift+Tab | Cycle pane focus |
| Ctrl+P | Command palette (global) |
| Ctrl+E | Toggle sidebar |
| Ctrl+B | Toggle bottom panel |
| / | Local filter/search for focused pane |
| z | Zoom/focus current pane (Esc to restore) |
| q | Back / close (context-dependent) |
| Ctrl+Q | Quit app |
| r | Refresh current view |
| ? | Help overlay |

**Browse mode:**

| Key | Action |
|---|---|
| j / k or arrows | Move cursor |
| Enter | Open / drill down |
| Backspace / h | Go back / parent |
| Space | Toggle select |
| f | Open filter editor |
| s | Cycle sort field |
| x | Context actions menu |

**Watch mode:**

| Key | Action |
|---|---|
| c | Cancel run (with confirmation) |
| L | Zoom logs |
| Ctrl+C | Detach (run continues) |
| a | Approve (when review ready) |

**Review mode:**

| Key | Action |
|---|---|
| j / k | Navigate findings |
| Enter | Drill into finding's resource |
| a | Approve |
| R | Reject (uppercase to prevent accidents) |
| d | Show diff |
| m | Add comment |

**Modes:** browse, select, command, watch, review, filter. Minimal and explicit.

### 7.8 Narrow terminal fallback

| Width | Behavior |
|---|---|
| >= 120 cols | Full 3-zone layout |
| 100-119 | Sidebar narrowed |
| 80-99 | Sidebar hidden by default, Ctrl+E as modal overlay |
| < 80 | Screen-switch mode: center only, bottom as toggle overlay, sidebar becomes palette navigation |

Layout adapts on resize events, instant, no restart.

**Screen-switch keybindings:** 1-9 switch screen by number, backtick toggles bottom overlay, Ctrl+E opens resource picker.

### 7.9 State persistence

Restored across restarts:

- Last profile/server
- Sidebar width, bottom height
- Last open URI and bottom tab (optional)

NOT restored: transient selections.

### 7.10 Theming and accessibility

Themes: dark (default), light, high contrast (WCAG AA). Set via `stitch-tui --theme <name>` or config.

**Color-agnostic status markers** (always color + symbol):

| Status | Color | Symbol |
|---|---|---|
| OK / Succeeded | Green | checkmark |
| Warning / Degraded | Orange | filled circle |
| Error / Failed | Red | X |
| Running / Active | Yellow | spinner |
| Pending / Queued | Gray | empty circle |
| Cancelled | Gray | dash |

`--no-animation` disables spinners and transitions. Textual built-in accessibility support for screen readers.

### 7.11 Standard view states

All screens handle these consistently:

| State | Behavior |
|---|---|
| Loading | Spinner with "Loading {resource_type}..." |
| Empty | "{Resource type} not found" or "No results match filter" |
| Partial data | Render available, mark missing sections |
| Stream unavailable | "Events offline, showing cached data" |
| Permission denied | "Insufficient capabilities for {capability}" |

---

## 8. Target Profiles

Constraints and responsibilities only. Full design deferred to each phase.

### 8.1 Minimal HTML (stitch-lite)

**Purpose:** Rescue UI, low-JS fallback, remote access, degraded networks.

**Constraints:**

- Server-rendered HTML (Jinja2 templates from FastAPI)
- Maximum JS: htmx or Alpine.js. No build step, no SPA framework.
- Must work with JS disabled for read-only operations
- Must work on mobile browsers
- SSE for live updates, polling fallback. No WebSocket requirement.

**Transport path:** Server-side local service adapter (templates call stitch-sdk in-process). HTTP loopback only if architecturally required. stitch-lite must not become a weird self-calling web tier.

**Responsibilities:** Browse resources, view details, run preflight/trace/impact via form submission, view run progress, view and act on reviews, view notifications, basic search.

**Non-goals:** Topology graph visualization, split panes, drag-and-drop, offline support, real-time keystroke interaction.

**Must reuse:** stitch-core types, stitch-sdk for server-side calls, capability discovery for auth-aware navigation, shared error model, resource URIs as page URLs.

### 8.2 Full WebUI (stitch-web)

**Purpose:** Main operator console. IDE-inspired rich client.

**Constraints:**

- React + TypeScript, TanStack Router + TanStack Query
- WebSocket for all live features
- Must pass "same actions as CLI" test
- Must NOT introduce WebUI-only actions

**Responsibilities:** Everything CLI/TUI do, plus topology canvas, multi-tab workspace, drag-and-drop layout, rich diff viewer, inline AI suggestion review, dashboard screens, saved views.

**Non-goals:** Offline-first (optional later), mobile-optimized (stitch-lite's job).

**Must reuse:** TypeScript types generated from stitch-core JSON schemas, same action names, URIs, filter grammar, lifecycle states, error codes, capability discovery.

### 8.3 Desktop GUI (stitch-desktop)

**Purpose:** Local-first power client. WebUI++ with native integrations.

**Constraints:**

- Tauri (Rust shell + web frontend). Wraps stitch-web.
- Desktop features are Tauri plugins, not web code.

**Responsibilities:** Everything stitch-web does, plus local filesystem access, SSH helper, system tray notifications, background sync, offline cache, native OS notifications, local agent bridge.

**Non-goals:** Being a separate product from stitch-web, platform-specific UI.

### 8.4 Shell Scripting Mode

**Purpose:** Automation, pipelines, CI/CD, cron, recovery scripts.

**Constraints:** stitch-cli with `--non-interactive` and `--output json|compact`. NOT a separate package.

**Feature parity rule:** If a command works interactively, it must work non-interactively with `--yes --non-interactive --output json`. No exceptions.

---

## 9. Phasing

| Phase | Deliverable | Depends on | Exit criteria |
|---|---|---|---|
| **0** | Rename `vos` -> `stitch` | Nothing | Clean namespace, all tests pass |
| **1** | stitch-core + stitch-sdk + stitch-cli | Phase 0 | `stitch device list`, `stitch preflight run --watch`, `stitch trace run 42 --from sw-core-01`, `stitch run watch <id>` all work against live lab |
| **2** | stitch-tui | Phase 1 | TUI can inspect device, watch run, approve review |
| **3** | stitch-lite | Phase 1 | Lite can browse, run preflight, view review |
| **4** | stitch-web | Phase 1 + schema export | Web achieves CLI action parity plus topology canvas |
| **5** | stitch-desktop | Phase 4 | Desktop adds native notifications + local file export |

**Note:** This spec uses `stitch.*` naming throughout. The current codebase uses `vos.*`. Phase 0 (rename) must complete before Phase 1 begins. During Phase 0, no architectural changes — mechanical rename only.

---

## 10. Dependency Rules

```
stitch-core     -> nothing (pure types, no IO)
stitch-sdk      -> stitch-core, httpx, websockets
stitch-cli      -> stitch-core, stitch-sdk, typer, rich
stitch-tui      -> stitch-core, stitch-sdk, textual
stitch-lite     -> stitch-core, stitch-sdk, jinja2 (server-side only)
stitch-web      -> stitch-core types (via JSON schema / OpenAPI codegen)
stitch-desktop  -> stitch-web (embedded)
```

**Hard rules:**

- No client imports another client
- All clients depend only on stitch-core + stitch-sdk (or generated types for TS)
- stitch-core has zero IO dependencies — pure data models and types
- stitch-sdk is the only package that talks to the network
- Domain layer (stitch.modelkit, stitch.contractkit, etc.) remains independent — operator layer imports domain types, never the reverse

**Schema source of truth:** `stitch-core` is the schema source of truth. OpenAPI/JSON Schema and TypeScript types are generated artifacts, not independently edited contracts.

**Test rule:** Every action exposed in any client must have a contract-level test through stitch-sdk. Client-specific tests cover rendering. Action correctness is verified at SDK/contract level.

---

## 11. Out of Scope for v1

- Command aliases / short commands
- Offline-first web
- Serial/UART integration
- Mobile-rich UI
- Generated screens from capabilities
- Desktop-only workflows
- Nested filter expressions
- Plugin/extension system for clients

---

## 12. Golden Flows

### Flow 1: Inspect device while watching a run

**CLI:**

```bash
# Terminal 1
stitch preflight run --scope site-rdam --watch

# Terminal 2
stitch device inspect sw-core-01
```

**TUI:**

1. Open TUI, navigate to sw-core-01 in sidebar
2. Press `Enter` to open device detail in center
3. Bottom panel shows run_4f8a progress streaming
4. Alert badge appears: "1 run active"
5. Press `w` to switch center to run watch (device detail is in back history)
6. Press `Backspace` to return to device detail, run still streaming in bottom

### Flow 2: Run preflight, review, approve from CLI

```bash
# Start preflight
stitch preflight run --scope site-rdam --watch

# Watch completes, shows: "Review ready: rev_001A"
# View review
stitch review show rev_001A

# See findings, approve
stitch review approve rev_001A --comment "VLAN 42 issue is known, accepting"
```

### Flow 3: Recover from stale stream in TUI

1. TUI top bar changes: "connected" -> "reconnecting (3s)"
2. Bottom panel shows: "Stream interrupted, buffered data shown"
3. After reconnect: "replaying 12 missed events..."
4. Events replay in order, bottom panel catches up
5. Top bar returns to "connected"
6. If replay fails (too old): "Stream reset - refreshing full state"
7. Current screen reloads from query, streams resume from current

---

## Appendix A: Glossary

### Product and naming

| Term | Meaning |
|---|---|
| **Stitch** | Product name. The multi-client operator platform. |
| **The Stitch** | Informal name for the running system. |

### Packages

| Package | Binary | Description |
|---|---|---|
| `stitch-core` | (library) | Pure types: command/query/stream models, URIs, UX contract |
| `stitch-sdk` | (library) | API client, stream client, auth/session |
| `stitch-cli` | `stitch` | CLI operator client |
| `stitch-tui` | `stitch-tui` | Terminal UI operator client |
| `stitch-lite` | (server module) | Minimal HTML client, server-rendered |
| `stitch-web` | (SPA) | Full WebUI operator client |
| `stitch-desktop` | `stitch-desktop` | Desktop wrapper (Tauri) |

### Domain layer (renamed from vos)

| Package | Description |
|---|---|
| `stitch_workbench` | Runtime spine |
| `stitch.contractkit` | Interaction protocols |
| `stitch.modelkit` | Domain data types |
| `stitch.graphkit` | Graph traversal |
| `stitch.storekit` | Topology serialization |
| `stitch.switchcraft` | Switch adapter |
| `stitch.opnsensecraft` | OPNsense adapter |
| `stitch.proxmoxcraft` | Proxmox adapter |
| `stitch.collectkit` | Observation merging |
| `stitch.verifykit` | Verification engine |
| `stitch.tracekit` | VLAN trace + impact |
| `stitch.interfacekit` | HTTP exposure layer |
| `stitch.agentcore` | AI orchestration |

### Conventions

| Convention | Pattern |
|---|---|
| URI scheme | `stitch:/{type}/{id}` |
| Action naming | `{namespace}.{verb}` (e.g., `run.create`, `review.approve`, `trace.run`). `{namespace}.{qualifier}.{verb}` reserved for future disambiguation if needed. |
| Canonical IDs | Opaque, prefixed: `dev_`, `port_`, `lnk_`, `run_`, `tsk_`, `stp_`, `rev_`, `rpt_`, `trc_`, `imp_`, `snap_`. Exceptions: VLANs use numeric IDs (`42`), modules use names (`switchcraft`), `topology/current` is a well-known alias. |
| Error codes | `{resource}.{condition}` or `{system}.{condition}` |
| Filter grammar | `--filter field<op>value`, ops: `= != > >= < <= ~ in` |
