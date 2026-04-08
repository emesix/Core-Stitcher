# VOS-Workbench — Alpha Contract Proposals

*Concrete proposals for all 12 alpha entry checklist items.
Written by Claude, revised with ChatGPT counter-proposals.*

**Status: Alpha freeze candidate.**
**Authority: This is the authoritative contract document for alpha implementation.
Where it conflicts with older docs, this document wins.**

---

## Round 1 — Foundations

### Proposal 4: Ontology — Everything is a module

**Decision:** There are not three separate concepts. There are two:

- **Module** — anything with a UUID, a type, a config, and a place in the tree.
  Whether it runs code internally or wraps an external connection, it's a module.
- **Node** — NOT a stored type. Nodes are a computed projection of the module
  tree for UI/navigation. They are generated at runtime, never persisted.

**Why collapse resources into modules?**

The line between "resource" and "module" is blurry. An SSH executor (`exec.ssh`)
manages an external connection AND runs internal logic. Is it a resource or a
module? It's both. Splitting them creates a classification problem that never
goes away.

Instead, use module type namespaces as **semantic families** to distinguish
behavior, lifecycle defaults, and policy treatment:

```
core.*         — runtime infrastructure (router, policy, eventbus)
exec.*         — execution surfaces (shell, ssh, api)
memory.*       — memory/state modules
model.*        — LLM provider adapters
resource.*     — external system wrappers (proxmox, opnsense, mcp)
integration.*  — bridges to external services (wiki, git)
client.*       — frontend adapters
worker.*       — ephemeral task workers
```

**Important:** "Everything is a module" does not mean all modules are
operationally the same. A `core.router`, `resource.proxmox`, and an
ephemeral `worker.coder` share identity/config/wiring mechanics but may
have different lifecycle rules, policy defaults, and health semantics
based on their family.

A `resource.proxmox` module wraps the Proxmox API. It has a UUID, config
(host, credentials), lifecycle (persistent), and capabilities (vm.create,
vm.list, etc.). It's a module. No special treatment needed.

**Node projection rules:**

Nodes are computed for UI/API consumption:

- Every active module becomes a node
- Runtime objects (tasks, sessions, artifacts) become nodes
- Inactive modules are hidden unless explicitly pinned
- The tree shape is: project root → config branches + runtime branches

**What this eliminates:**

- The `resources/` directory in the config tree — resources are just
  modules in `modules/resource-proxmox/module.yaml`
- The `node.schema.json` — nodes are API response objects, not stored entities
- The three-way identity confusion

**Pydantic base:**

```python
class ModuleFamily(str, Enum):
    CORE = "core"
    EXEC = "exec"
    MEMORY = "memory"
    MODEL = "model"
    RESOURCE = "resource"
    INTEGRATION = "integration"
    CLIENT = "client"
    WORKER = "worker"

class ModuleInstance(BaseModel):
    uuid: UUID4
    name: str  # unique within project
    type: str  # e.g. "exec.ssh", "resource.proxmox"
    lifecycle: Literal["persistent", "ephemeral"]
    enabled: bool = True
    config: dict[str, Any] = {}  # validated against type's config_model
    wiring: ModuleWiring = ModuleWiring()
    visibility: ModuleVisibility = ModuleVisibility()

    @computed_field
    @property
    def family(self) -> ModuleFamily:
        """Derived from type prefix, never stored."""
        return ModuleFamily(self.type.split(".")[0])
```

---

### Proposal 3: URI Grammar

**Decision:** Custom URI schemes following RFC 3986 structure.

**Schemes:**

| Scheme | Format | Resolves to |
|--------|--------|-------------|
| `module` | `module://name/<module-name>` | Module by name |
| `module` | `module://uuid/<module-uuid>` | Module by UUID |
| `module` | `module://<module-name>` (shorthand) | Same as `module://name/...` |
| `secret` | `secret://<provider>/<key>` | Secret value (never serialized back) |
| `system` | `system://<service>` | System singleton (eventbus, registry) |
| `capability` | `capability://<name>` | Set of modules providing it |

**Examples:**

```yaml
# By name — preferred for human-authored config
policy: module://name/policy-main
memory: module://memory-main              # shorthand, equivalent to module://name/memory-main

# By UUID — used by runtime, ephemeral workers
parent: module://uuid/2db742d5-5f23-4ce0-9c83-7d4dbf18e2c3

# Secrets
api_key: secret://env/ANTHROPIC_API_KEY
ssh_key: secret://file/~/.ssh/id_ed25519
password: secret://pass/proxmox/root

# System services
event_bus: system://eventbus
registry: system://registry

# Capability selectors (returns set of modules)
model: capability://chat.fast
```

**Resolution rules:**

- `module://name/x`: search modules by `name` field, must be unique
- `module://uuid/x`: direct UUID lookup
- `module://x` (bare): treated as `module://name/x` — the shorthand
- **Module names must not match UUID regex** (prevents ambiguity entirely)
- Unresolvable refs: return `UnresolvableReference` error with URI + reason

**Resolution timing:**

- `module://` → eager at semantic validation (startup)
- `system://` → eager at semantic validation (startup)
- `secret://` → reference validation eager, value resolution lazy or
  startup-required per module type declaration (see Proposal 6)
- `capability://` → resolved at call site when the selector is evaluated

**Parser (Pydantic):**

```python
class VosReference(BaseModel):
    scheme: Literal["module", "secret", "system", "capability"]
    authority: str | None = None  # "name", "uuid", provider name, or None
    path: str
    raw: str  # original string

    @classmethod
    def parse(cls, uri: str) -> "VosReference": ...

    def resolve(self, registry: "ModuleRegistry") -> Any: ...
    def is_resolvable(self, registry: "ModuleRegistry") -> bool: ...
```

**Name hygiene rule:**

```python
import re
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)

class ModuleConfig(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_must_not_look_like_uuid(cls, v: str) -> str:
        if UUID_PATTERN.match(v):
            raise ValueError("Module names must not match UUID format")
        return v
```

**What this eliminates:**

- The `resource://` scheme — resources are modules, use `module://`
- The `model://` scheme — model adapters are modules, use `module://`
- Name/UUID ambiguity — structurally impossible

---

### Proposal 5: Settings Merge Semantics

**Decision:** Deterministic, simple, no magic.

**Rules:**

| Data type | Merge behavior | Example |
|-----------|---------------|---------|
| Scalar | Higher layer replaces | `runtime.mode = "exec"` wins over `project.mode = "plan"` |
| Dict | Recursive deep merge, higher keys win | `{a:1, b:2}` + `{b:3, c:4}` → `{a:1, b:3, c:4}` |
| List | Replace wholesale | `project.tags: [a,b]` + `local.tags: [c]` → `[c]` |
| `null` | Explicit remove | `local.debug: null` removes `project.debug: true` |
| Absent key | Inherit from lower layer | Key not in `local` → use `project` value |
| Secret ref | Pass through unchanged | `secret://env/X` survives merge, resolved separately |
| VOS ref | Pass through unchanged | `module://x` survives merge, resolved separately |

**No keyed list merge.** Lists are always replaced. If you need keyed merge
behavior, use a dict instead. This avoids the #1 source of config merge bugs.

**Implementation:**

```python
def merge_two(base: dict, override: dict) -> dict:
    """Merge override into base. Override wins."""
    result = dict(base)
    for key, value in override.items():
        if value is None:
            result.pop(key, None)  # null = remove
        elif isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_two(result[key], value)  # recurse
        else:
            result[key] = value  # replace (scalars, lists, everything else)
    return result

def merge_layers(
    managed: dict,
    bootstrap: dict,
    project: dict,
    local: dict,
    runtime: dict,
) -> tuple[dict, dict[str, str]]:
    """Returns (effective_config, value_sources).
    value_sources maps dotted key paths to layer names for tracing."""
    ...
```

**Trace function:** Every merged value tracks which layer it came from.
`trace_value("config.mode")` returns `("execution", "runtime")`.

---

## Round 2 — Config Schemas

### Proposal 1: workbench.yaml Schema

```python
class StateBackends(BaseModel):
    desired: Literal["git"] = "git"
    durable_runtime: Literal["sqlite", "postgres"] = "sqlite"
    ephemeral_runtime: Literal["memory"] = "memory"
    artifacts: Literal["filesystem"] = "filesystem"

class CommunicationConfig(BaseModel):
    direct_calls: Literal["runtime-mediated"] = "runtime-mediated"
    events: Literal["pubsub"] = "pubsub"
    module_to_module_direct: bool = False

class WiringConfig(BaseModel):
    default_mode: Literal["explicit", "selector"] = "explicit"
    selector_mode: Literal["optional", "disabled"] = "optional"

class EphemeralConfig(BaseModel):
    visible_in_runtime: bool = True
    persisted_in_desired_tree: bool = False
    require_parent_task: bool = True
    require_budget: bool = True
    archive_on_exit: bool = True

class SettingsLayer(str, Enum):
    MANAGED = "managed"
    BOOTSTRAP = "bootstrap"
    PROJECT = "project"
    LOCAL = "local"
    RUNTIME = "runtime"

class ProjectConfig(BaseModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9._-]+$")
    name: str
    version: int = 1

class WorkbenchConfig(BaseModel):
    schema_version: int = 1  # separate from project version, tracks config format
    project: ProjectConfig
    settings_precedence: list[SettingsLayer] = [
        SettingsLayer.MANAGED,
        SettingsLayer.BOOTSTRAP,
        SettingsLayer.PROJECT,
        SettingsLayer.LOCAL,
        SettingsLayer.RUNTIME,
    ]
    state: StateBackends = StateBackends()
    communication: CommunicationConfig = CommunicationConfig()
    wiring: WiringConfig = WiringConfig()
    ephemeral_modules: EphemeralConfig = EphemeralConfig()
```

---

### Proposal 2: module.yaml Schema

```python
class Dependency(BaseModel):
    ref: str                              # module:// URI
    kind: Literal["hard", "soft"] = "hard"  # hard = fail if missing, soft = degrade

class ModuleWiring(BaseModel):
    depends_on: list[Dependency] = []     # typed dependencies
    provides: list[str] = []              # capability:// URIs

class ModuleVisibility(BaseModel):
    can_see: list[str] = []           # module:// URIs

class BudgetConfig(BaseModel):
    max_tokens: int | None = None
    max_seconds: float | None = None
    max_tool_calls: int | None = None

class ModuleConfig(BaseModel):
    uuid: UUID4
    name: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    type: str = Field(pattern=r"^[a-z]+\.[a-z][a-z0-9._-]*$")
    lifecycle: Literal["persistent", "ephemeral"] = "persistent"
    enabled: bool = True
    config: dict[str, Any] = {}       # validated against type's config_model
    wiring: ModuleWiring = ModuleWiring()
    visibility: ModuleVisibility = ModuleVisibility()
    budget: BudgetConfig | None = None  # required for ephemeral
```

**Directory name rule:** Module directory name MUST match the `name` field.
So `modules/router-main/module.yaml` must contain `name: router-main`.

---

### Proposal 6: Config Validation Lifecycle

**Two-phase validation:**

1. **Schema validation** — at file load time (Pydantic parse)
   - YAML syntax correct
   - All required fields present
   - Field types match schema
   - Regex patterns pass (name, type, uuid format)
   - Does NOT resolve references — `module://x` is just a valid string here

2. **Semantic validation** — at module instantiation time
   - All `module://` references resolve to real modules
   - All `system://` references resolve to real services
   - All `depends_on` targets exist and are not circular
   - Module type exists in registry
   - Config dict validates against the module type's `config_model`
   - Budget is present if lifecycle is ephemeral

3. **Secret validation** — split into two sub-levels

   **3A. Secret reference validation** (at startup):
   - `secret://` URI is syntactically valid
   - Provider (env, file, pass, vault) is known/registered
   - Consuming config field is allowed to hold a secret reference

   **3B. Secret value resolution** (timing depends on module type):
   - `startup_required` secrets: resolved at startup, module fails if missing
   - `lazy_allowed` secrets: resolved at first use, module may start without

   Each module type declares which secret-bearing config keys are
   startup-required vs lazy-allowed:

   ```python
   class SecretRequirement(str, Enum):
       STARTUP_REQUIRED = "startup_required"
       LAZY_ALLOWED = "lazy_allowed"

   class ModuleType(Protocol):
       secret_requirements: dict[str, SecretRequirement]
       # key = config field path, value = requirement level
   ```

**Failure behavior:**

- Schema validation failure: refuse to load, log error, exit if workbench.yaml
- Semantic validation failure: module enters `failed` state with error detail,
  system continues (other modules still start)
- Secret reference invalid: semantic validation failure
- Startup-required secret missing: module enters `failed`
- Lazy secret missing at first use: action fails with structured error,
  module may remain `active` or become `degraded` per module policy
- Config that passes schema but fails semantic: allowed to exist on disk,
  caught at startup

**No partial configs.** A module's config must be complete and valid to start.
If you want optional fields, make them `Optional` in the Pydantic model with
defaults.

---

## Round 3 — Runtime

### Proposal 7: Module Type Registry

**Use Python entry points.**

A module type is a Python class that implements:

```python
from typing import Protocol

class ModuleType(Protocol):
    """Every module type must implement this."""

    type_name: str                    # e.g. "exec.ssh"
    version: str                      # semver
    config_model: type[BaseModel]     # Pydantic model for config validation
    capabilities: list[str]           # what this type provides

    async def start(self, instance: ModuleInstance, runtime: Runtime) -> None:
        """Called when the module is started."""
        ...

    async def stop(self) -> None:
        """Called when the module is stopped."""
        ...

    async def health(self) -> HealthStatus:
        """Called for health checks."""
        ...
```

**Registration via pyproject.toml:**

```toml
[project.entry-points."vos.modules"]
"exec.shell" = "vos_workbench.modules.exec_shell:ShellModule"
"exec.ssh" = "vos_workbench.modules.exec_ssh:SSHModule"
"core.router" = "vos_workbench.modules.core_router:RouterModule"
"resource.proxmox" = "vos_workbench.modules.resource_proxmox:ProxmoxModule"
```

**Discovery:**

```python
from importlib.metadata import entry_points

def discover_module_types() -> dict[str, type[ModuleType]]:
    types = {}
    for ep in entry_points(group="vos.modules"):
        types[ep.name] = ep.load()
    return types
```

**Third-party modules:** Install a pip package that declares `vos.modules`
entry points. They appear automatically.

---

### Proposal 8: Bootstrap / Startup Sequence

**Use `graphlib.TopologicalSorter`.**

```python
from graphlib import TopologicalSorter

def compute_startup_order(modules: list[ModuleConfig]) -> list[list[str]]:
    """Returns groups of modules that can start in parallel."""
    graph = {}
    for mod in modules:
        deps = [VosReference.parse(dep.ref).path for dep in mod.wiring.depends_on]
        graph[mod.name] = set(deps)

    sorter = TopologicalSorter(graph)
    sorter.prepare()

    order = []
    while sorter.is_active():
        group = list(sorter.get_ready())
        order.append(group)
        for name in group:
            sorter.done(name)
    return order
```

**Rules:**

- Circular dependency: `graphlib.CycleError` → refuse to start, log the cycle
- Startup timeout: 30 seconds per module default, configurable per module
- **Hard** dependency fails/disabled **at startup**: dependent enters `failed`
- **Hard** dependency dies **after startup**: dependent enters `degraded`,
  then `failed` if recovery does not happen within restart window
- **Soft** dependency fails/disabled: dependent starts (or continues) with
  reduced capability, enters `degraded`
- Modules in the same topo group start concurrently (`asyncio.TaskGroup`)
- **Alpha constraint:** `depends_on` refs must use module names
  (`module://name/x` or `module://x`), not UUIDs. UUID refs are runtime-only.
- **Alpha simplification:** No special "system modules start first" rule.
  System modules that must start first should be modeled as explicit
  dependencies. DAG ordering handles the rest.

**Restart policy for persistent modules:**

```python
class RestartPolicy(BaseModel):
    max_restarts: int = 3
    backoff_seconds: list[float] = [1.0, 5.0, 30.0]
    reset_after_seconds: float = 300.0  # reset counter after 5min of health
```

---

### Proposal 9: Event Bus Contract

**In-process asyncio pub/sub + SQLite persistence.**

**Event envelope (CloudEvents-inspired):**

```python
class VosEvent(BaseModel):
    id: UUID4 = Field(default_factory=uuid4)
    type: str                          # e.g. "task.started", "module.degraded"
    source: str                        # module:// URI of emitter
    time: datetime = Field(default_factory=datetime.utcnow)
    project_id: str
    correlation_id: UUID4 | None = None  # links related events
    causation_id: UUID4 | None = None    # the event that caused this one
    data: dict[str, Any] = {}
    severity: Literal["debug", "info", "warning", "error"] = "info"
```

**Subscription:**

```python
class EventBus:
    async def publish(self, event: VosEvent) -> None: ...
    async def subscribe(
        self,
        subscriber_id: str,
        event_types: list[str] | None = None,  # None = all
        source_filter: str | None = None,       # glob on source URI
    ) -> AsyncIterator[VosEvent]: ...
```

**Delivery guarantees:**

- In-process: at-most-once (if subscriber is slow, events are dropped after
  buffer fills — buffer size configurable, default 1000).
  **Overflow visibility:** when a subscriber's buffer overflows, emit a
  `bus.subscriber.overflow` event and mark the subscriber as `degraded`.
  Silent drops are not acceptable for debugging.
- Persisted: all events with severity >= `info` are written to SQLite
- Replay: subscribers can request events from a timestamp or event ID
- Ordering: per-source FIFO guaranteed, global ordering best-effort

**Scope:** All events carry `project_id`. Subscribers can filter by project.
For alpha, single-project only.

---

### Proposal 10: Frontend API Contract

**FastAPI + WebSocket.**

**REST endpoints (CRUD):**

```
GET    /api/v1/project                  → project info
GET    /api/v1/tree/config              → config tree (modules, policies, views)
GET    /api/v1/tree/runtime             → runtime tree (sessions, tasks, workers, health)
GET    /api/v1/modules                  → list all modules
GET    /api/v1/modules/{uuid}           → module detail + status
POST   /api/v1/modules/{uuid}/start     → start a module
POST   /api/v1/modules/{uuid}/stop      → stop a module
GET    /api/v1/config/effective          → merged effective config
GET    /api/v1/config/trace/{key_path}  → which layer set this value
GET    /api/v1/tasks                    → list tasks
GET    /api/v1/tasks/{uuid}             → task detail
GET    /api/v1/health                   → system + per-module health
GET    /api/v1/events?since=...&type=.. → query event log
```

**WebSocket (streaming):**

```
WS /api/v1/ws/events                   → live event stream
WS /api/v1/ws/tasks/{uuid}             → live task updates
```

**Authentication (alpha):**

- API key in `Authorization: Bearer <key>` header
- Key defined in bootstrap config
- Single-user for alpha, multi-user later

**Response format:**

```json
{
  "data": { ... },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  }
}
```

---

### Proposal 11: Runtime Storage Contract

**SQLModel + Alembic.**

**Core tables:**

```python
class SessionRecord(SQLModel, table=True):
    id: UUID4 = Field(primary_key=True)
    project_id: str
    started_at: datetime
    ended_at: datetime | None
    status: str  # active, completed, abandoned
    metadata_: dict = Field(sa_column=Column(JSON))

class TaskRecord(SQLModel, table=True):
    id: UUID4 = Field(primary_key=True)
    session_id: UUID4 = Field(foreign_key="sessionrecord.id")
    parent_task_id: UUID4 | None
    module_uuid: UUID4  # which module owns this task
    status: str  # pending, running, completed, failed, cancelled
    created_at: datetime
    updated_at: datetime
    result_summary: str | None
    budget_used: dict | None = Field(sa_column=Column(JSON))

class EventRecord(SQLModel, table=True):
    id: UUID4 = Field(primary_key=True)
    type: str = Field(index=True)
    source: str
    project_id: str = Field(index=True)
    time: datetime = Field(index=True)
    correlation_id: UUID4 | None
    causation_id: UUID4 | None
    severity: str
    data: dict = Field(sa_column=Column(JSON))

class ModuleHealthRecord(SQLModel, table=True):
    id: int = Field(primary_key=True)
    module_uuid: UUID4 = Field(index=True)
    status: str  # active, degraded, failed, stopped
    checked_at: datetime
    details: dict | None = Field(sa_column=Column(JSON))

class MemoryEntry(SQLModel, table=True):
    id: UUID4 = Field(primary_key=True)
    project_id: str
    scope: str  # session, working, stable, archived
    content_type: str
    content: str  # or path to file for large content
    created_at: datetime
    updated_at: datetime
    source_module: UUID4 | None
    verification_state: str  # draft, derived, approved, deprecated
    metadata_: dict = Field(sa_column=Column(JSON))

class ConvergenceRecord(SQLModel, table=True):
    id: int = Field(primary_key=True)
    scope: str  # module UUID or "global"
    status: str  # converged, pending, degraded, drifted, failed
    checked_at: datetime
    desired_hash: str
    actual_hash: str
    diffs: dict | None = Field(sa_column=Column(JSON))
```

**Artifacts** stay on filesystem under `{state_dir}/artifacts/{task_uuid}/`.

**Migrations:** Alembic with auto-generation from SQLModel changes.

---

### Proposal 12: Error and Supervision Contract

**Error shape (3-tier exposure model):**

```python
class WorkbenchError(BaseModel):
    error_id: UUID4 = Field(default_factory=uuid4)
    source_module: UUID4 | None  # which module produced this
    severity: Literal["warning", "error", "fatal"]
    category: Literal[
        "config",       # bad config, validation failure
        "dependency",   # dependency unavailable
        "execution",    # tool/command failed
        "budget",       # budget exhausted
        "policy",       # policy denied action
        "provider",     # LLM provider error
        "internal",     # unexpected runtime error
    ]
    retryable: bool
    message: str              # Tier 2: structured, operator-meaningful
    user_summary: str         # Tier 3: short, for UI lists and health screens
    details: dict[str, Any] = {}   # Tier 2: bounded, redacted
    detail_truncated: bool = False  # True if details were size-limited
    artifact_ref: str | None = None # Tier 1: link to full context in logs/artifacts
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

**3-tier exposure:**

| Tier | Where | Content | Rules |
|------|-------|---------|-------|
| 1. Full context | Logs + artifacts | Stack traces, raw payloads, stderr | Redacted for secrets, linked via `artifact_ref` |
| 2. API/events | REST responses, WebSocket, event bus | `message` + bounded `details` | Max 16KB serialized, secrets redacted, `detail_truncated` flag |
| 3. Human summary | TUI/GUI health screens | `user_summary` | Short, readable, severity-tagged |

**Supervision rules:**

| Module type | On failure | Max restarts | Backoff |
|-------------|-----------|--------------|---------|
| Persistent | Restart with backoff | 3 (configurable) | 1s, 5s, 30s |
| Persistent (3 failures) | Mark `failed`, emit event | — | — |
| Ephemeral | No restart, report to parent | 0 | — |
| System (eventbus, registry) | Restart immediately | 5 | 0.5s, 1s, 2s, 5s, 10s |

**Propagation:**

- Module fails → event emitted (`module.failed`)
- Dependents of failed module → check if dependency is hard or soft
  - Hard dependency at startup: dependent enters `failed`
  - Hard dependency at runtime: dependent enters `degraded`, then `failed`
    if recovery does not happen within restart window
  - Soft dependency: dependent continues with reduced capability as `degraded`
- Ephemeral agent fails → parent coordinator receives `WorkbenchError`
  in task result, decides whether to retry with new agent or fail the task
- All errors are logged via `structlog` AND emitted as events

**Frontend surfacing:**

- `GET /api/v1/health` returns per-module health with `user_summary`
- WebSocket `module.failed` events stream bounded `details` to frontends
- Full diagnostics available via `artifact_ref` for deep inspection
- Secret values must never appear in any tier unredacted

---

## Summary of key design choices

| Choice | Rationale |
|--------|-----------|
| Everything is a module | Eliminates resource/node confusion, one registry |
| Module families are semantic, not structural | Lifecycle/policy differ by family, but identity/config/wiring are uniform |
| No `resource://` or `model://` schemes | They're all `module://` |
| `module://name/x` vs `module://uuid/x` | No ambiguity, names forbidden from matching UUID regex |
| Nodes are computed, not stored | UI concern, not a storage concern |
| Lists replace, never merge | #1 source of config bugs eliminated |
| Eager URI resolution for modules, lazy for secrets | Fail fast on wiring, tolerate missing secrets at startup |
| Secret validation split: reference vs value | Reference checked at startup, value resolution per module type policy |
| Two-phase validation (schema + semantic) | Catch typos at load, catch wiring at startup |
| Hard vs soft dependencies | Hard = fail if missing, soft = degrade gracefully |
| Python entry_points for type registry | Standard, pip-installable, zero custom infra |
| graphlib for startup order | Stdlib, correct, handles parallel groups |
| CloudEvents-inspired envelope | Standard shape, don't invent |
| Event bus overflow visibility | Degraded subscriber state, not silent drops |
| API key auth for alpha | Simple, upgrade later |
| Tree endpoints in API | System is tree-centered, API should reflect that |
| SQLModel for storage | FastAPI author's library, Pydantic + SQLAlchemy |
| Large blobs on filesystem, not SQLite | DB = index + metadata, FS = artifacts + transcripts |
| No restart for ephemeral modules | Parent decides, not the runtime |
| 3-tier error exposure | Full context in logs, bounded in API, summary in UI |

---

## Revision history

- **v1** (Claude): Initial proposals for all 12 items
- **v2** (Claude + ChatGPT): Integrated 4 counter-proposals:
  1. Ontology: added `worker.*` family, explicit semantic family rules
  2. URI grammar: `name/` and `uuid/` subpaths, UUID-shaped names forbidden
  3. Validation: secret reference vs value split, startup_required/lazy_allowed
  4. Error surfacing: 3-tier exposure model, bounded + redacted details
  Also integrated: schema_version, enum-backed precedence, hard/soft
  dependencies, event bus overflow visibility, tree API endpoints,
  blob-on-filesystem policy

---

*Post-review revision. Ready for final freeze decision.*
