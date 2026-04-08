# VOS-Workbench — Alpha Counter-Proposals (ChatGPT)

*Focused response to the 4 areas in `alpha-proposals.md` that I would revise before freeze.*

This document does **not** replace the full alpha proposal pack.
It only counter-proposes concrete solutions for the areas where I disagreed or wanted tighter wording.

---

## Scope

These 4 areas are adjusted here:

1. Ontology wording and semantics
2. URI grammar ambiguity
3. Validation lifecycle for secrets
4. Error surfacing and detail exposure

Everything else in `alpha-proposals.md` is assumed accepted for now unless challenged separately.

---

## 1. Counter-proposal: Ontology

### Problem with the current wording

The phrase **"everything is a module"** is useful as an alpha simplification, but it risks flattening important semantic differences.

A `core.router`, an `exec.shell`, a `resource.proxmox`, and an ephemeral coding worker can all be stored as module instances without being operationally identical.

### Counter-proposal

**Persisted config objects:** only **module instances**.

**Computed projection objects:** **nodes**.

**Semantic family:** derived from the module type prefix.

So the frozen ontology becomes:

- **Module instance** — the only persisted config object kind
- **Node** — computed projection for UI/API/runtime navigation
- **Module family** — semantic class derived from `type` prefix

### Module families

```text
core.*         runtime infrastructure
exec.*         execution surfaces
memory.*       memory/state helpers
model.*        model adapters
resource.*     external system wrappers
integration.*  bridges to external services
client.*       frontend adapters
worker.*       ephemeral task workers (optional explicit family)
```

### Rules

1. All persisted objects under `modules/` are module instances.
2. There is no separate persisted `resource` object kind.
3. `resource.*` remains a **semantic family**, not a separate config ontology.
4. Nodes are always computed and never stored in config or runtime DB as the source of truth.
5. Lifecycle, policy defaults, and health semantics may differ by module family.

### Why this is better than pure flattening

It keeps the simplification:
- one registry
- one identity model
- one wiring system
- one reference scheme

But preserves the important truth:
- not all modules behave the same
- not all modules have the same lifecycle expectations
- not all modules should receive the same policy defaults

### Frozen wording

> Everything persisted in the tree is a module instance.
> Nodes are computed projections.
> “Resource” is not a separate persisted object kind, but a semantic module family (`resource.*`).

---

## 2. Counter-proposal: URI Grammar

### Problem with the current wording

The current proposal allows both:

- `module://policy-main`
- `module://2db742d5-5f23-4ce0-9c83-7d4dbf18e2c3`

and resolves ambiguity by saying UUID wins if a name looks like a UUID.

That is avoidable complexity.

### Counter-proposal

Use **typed module references** so names and UUIDs are never ambiguous.

### Schemes

| Scheme | Format | Resolves to |
|--------|--------|-------------|
| `module` | `module://name/<module-name>` | Module by name |
| `module` | `module://uuid/<module-uuid>` | Module by UUID |
| `secret` | `secret://<provider>/<key>` | Secret value |
| `system` | `system://<service>` | Runtime singleton |
| `capability` | `capability://<name>` | Capability selector |

### Examples

```yaml
policy: module://name/policy-main
memory: module://name/memory-main
parent: module://uuid/2db742d5-5f23-4ce0-9c83-7d4dbf18e2c3
api_key: secret://env/ANTHROPIC_API_KEY
event_bus: system://eventbus
model_selector: capability://chat.fast
```

### Rules

1. Human-authored config should prefer `module://name/...`.
2. Runtime-generated references may use `module://uuid/...`.
3. Module names must still be unique within the project.
4. Module names should also be forbidden from matching UUID regex for hygiene, even though the grammar now avoids ambiguity.
5. `capability://` may resolve to one or more modules depending on call site.

### Why this is better

- no ambiguity rule needed
- easier parsing and validation
- clearer error messages
- runtime vs human references are visibly distinct

### Parser shape

```python
class VosReference(BaseModel):
    scheme: Literal["module", "secret", "system", "capability"]
    authority: str | None = None      # e.g. "name", "uuid", provider name
    path: str
    raw: str
```

### Resolution timing

- `module://...` → eager at semantic validation time
- `system://...` → eager at semantic validation time
- `secret://...` → lazy by default, optionally eager if a module marks the secret as startup-required
- `capability://...` → resolved when the consuming call site evaluates the selector

---

## 3. Counter-proposal: Validation Lifecycle for Secrets

### Problem with the current wording

The current two-phase validation is good, but it treats secret resolution too much like ordinary dependency validation.

That is too rigid for alpha.

Some modules need secrets only when first used, not at startup.

### Counter-proposal

Keep **two-phase validation**, but split secret validation into two sub-levels.

### Phase 1 — Schema validation

At file load:
- YAML syntax valid
- required fields present
- field types valid
- regex patterns valid
- secret references parsed as syntactically valid URIs

No value resolution yet.

### Phase 2 — Semantic validation

At module instantiation/startup:
- module type exists
- `module://` references resolve
- `system://` references resolve
- module config validates against its `config_model`
- ephemeral budget exists if lifecycle is ephemeral

### Secret validation split

#### 2A. Secret reference validation
At startup:
- provider in `secret://provider/...` is known
- URI is structurally valid
- consuming field is allowed to carry a secret reference

#### 2B. Secret value validation
Policy- and module-dependent:
- **startup-required secret** → resolve at startup, module fails if unavailable
- **lazy-use secret** → resolve at first real use, module may start without the value

### Module type hook

Each module type may declare which secret-bearing config keys are:
- `startup_required`
- `lazy_allowed`

Example:

```python
class SecretRequirement(str, Enum):
    STARTUP_REQUIRED = "startup_required"
    LAZY_ALLOWED = "lazy_allowed"

class ModuleType(Protocol):
    secret_requirements: dict[str, SecretRequirement]
```

### Failure behavior

- syntax-invalid secret ref → schema validation failure
- unknown provider → semantic validation failure
- startup-required secret missing → module enters `failed`
- lazy secret missing at first use → action fails with structured provider/secret error, module may remain `active` or become `degraded` depending on module policy

### Why this is better

- fail fast on bad wiring
- do not force all credentials to exist at startup
- supports alpha systems where some integrations are optional or only occasionally used

---

## 4. Counter-proposal: Error Surfacing

### Problem with the current wording

The current proposal says:

> Error details are never truncated — full context in `details` dict

That is too aggressive.

It risks:
- secret leakage
- giant payloads in API responses
- unstable frontend rendering
- mixing forensic logs with operator-facing error summaries

### Counter-proposal

Split error exposure into **three tiers**.

### Tier 1 — Runtime/internal full context
Stored in structured logs and/or artifacts.

May include:
- full stack traces
- raw provider payloads
- subprocess stderr
- deep debug fields

Must still be redacted for secrets.

### Tier 2 — Event/API details
Sent to frontends and event streams.

Must be:
- structured
- redacted
- size-bounded
- operator-meaningful

### Tier 3 — Human summary
Displayed in TUI/GUI lists and health screens.

Must be:
- short
- readable
- severity-tagged
- linked to richer context

### Revised error model

```python
class WorkbenchError(BaseModel):
    error_id: UUID4 = Field(default_factory=uuid4)
    source_module: UUID4 | None
    severity: Literal["warning", "error", "fatal"]
    category: Literal[
        "config",
        "dependency",
        "execution",
        "budget",
        "policy",
        "provider",
        "internal",
    ]
    retryable: bool
    message: str
    user_summary: str
    details: dict[str, Any] = {}
    detail_truncated: bool = False
    artifact_ref: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

### Rules

1. `details` in API/event payloads must be redacted before emission.
2. `details` must be size-bounded (for example 16 KB max serialized size in alpha).
3. Oversized details are truncated and `detail_truncated = true` is set.
4. Full diagnostic context should be written to logs/artifacts and linked via `artifact_ref`.
5. Secret values must never appear in API/event details, logs, or artifacts unredacted.

### Frontend behavior

- health views show `user_summary`
- task/event views show `message` + bounded `details`
- deep inspection may follow `artifact_ref`

### Why this is better

- safer by default
- predictable frontend payload sizes
- better separation between operator UX and forensic detail
- still preserves full diagnosability through artifacts/logs

---

## Net effect of these counter-proposals

These changes do **not** overturn the alpha plan.
They tighten it.

### Keep

- module-centric design
- computed nodes
- simple URI family
- two-phase validation
- strong error contract

### Tighten

- semantic module families remain explicit
- URI references become unambiguous
- secret validation becomes startup-vs-lazy aware
- error exposure becomes tiered, redacted, and bounded

---

## Recommendation

If these are accepted, the next edit to `alpha-proposals.md` should be a targeted revision, not a rewrite.

Suggested status labels:

- **Accept with wording change** → ontology
- **Accept with syntax change** → URI grammar
- **Accept with lifecycle split** → secrets validation
- **Accept with safety tightening** → error surfacing

---

*Counter-proposals should be evaluated against simplicity, safety, and alpha-readiness — not against theoretical elegance alone.*
