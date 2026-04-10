# Alpha Executor Routing Design

**Date:** 2026-04-10
**Status:** Approved
**Scope:** Wire real AI backends into agentcore, add deterministic routing policy, prove the full orchestration loop in read-only alpha.

---

## 1. Problem

Agentcore has a complete orchestration loop (plan, execute, summarize, review, correct) but every AI step goes to the same executor. There is no routing policy, no fallback chain, and no way to use different backends for different task kinds.

Meanwhile, the INTELL-A770 box is a multi-capability local node — not a single-purpose chat endpoint:

| Capability | Endpoint | What it does | Current status |
|---|---|---|---|
| GPU inference (Qwen2.5-7B) | `172.16.0.109:8000` | Chat, summarize, review, analysis | ~44 tok/s on one A770 GPU |
| CPU inference (TinyLlama) | `172.16.0.109:8001` | Lighter/faster inference, available at boot | ~33 tok/s |
| GPU.1 inference (TinyLlama) | `172.16.0.109:8002` | Second GPU slot, parallel work | ~81 tok/s |
| Sidecar (compute/work) | `172.16.0.109:8080` | Health, stage status, structured work dispatch | Stage FULL |
| Staged readiness | — | CPU-first, GPU loads after | Built into OVMS startup |
| 72 CPU threads | — | Shell, lint, test, git ops | Available via sidecar |

If the alpha only proves "summary goes to local GPU," it treats this machine as a summarization appliance. The alpha should prove that routing can use the same node flexibly based on capability, readiness, and task kind.

---

## 2. Design

### 2.1 Transport: configurable executor endpoints

**Current problem:** `OpenAICompatibleExecutor` hardcodes the chat completions URL as `{base_url}/chat/completions` and the health check as `{base_url}/models`. OVMS serves chat at `/v3/chat/completions`. OpenRouter serves at `/api/v1/chat/completions` and models at `/api/v1/models`.

**Fix:** Separate origin from path in `OpenAIExecutorConfig`:

```python
class OpenAIExecutorConfig(BaseModel):
    base_url: str          # bare origin only: "http://172.16.0.109:8000"
    api_path: str = "/v1/chat/completions"   # versioned chat route
    models_path: str | None = "/v1/models"   # health probe path, None = skip
    model: str = "gpt-4o-mini"
    api_key_env: str = "OPENAI_API_KEY"
    timeout: float = 60.0
    max_tokens: int = 4096
    temperature: float = 0.0
    domains: list[str] = []
    executor_id: str = "openai-compat"
```

URL construction becomes:
- Chat: `{base_url}{api_path}`
- Health: `{base_url}{models_path}` (or skip if `models_path is None`)

**Convention:** `base_url` is always the bare origin. Never include a path component in it. The path goes in `api_path` or `models_path`.

### 2.2 Executor instances

Four runtime backends. Two categories:

**Inference executors** (speak chat completions):

| ID | Class | Origin | API path | Models path | Model |
|---|---|---|---|---|---|
| `local-gpu` | `LocalExecutor` | `172.16.0.109:8000` | `/v3/chat/completions` | `None` (OVMS has no guaranteed models endpoint) | Qwen2.5-7B-Instruct-INT4 |
| `local-cpu` | `LocalExecutor` | `172.16.0.109:8001` | `/v3/chat/completions` | `None` | TinyLlama-1.1B-INT4 |
| `openrouter` | `OpenAICompatibleExecutor` | `https://openrouter.ai` | `/api/v1/chat/completions` | `/api/v1/models` | configurable (default: `anthropic/claude-sonnet-4`) |

**Work executor** (does not speak chat completions):

| ID | Class | Origin | Role |
|---|---|---|---|
| `local-sidecar` | `SidecarExecutor` (new) | `172.16.0.109:8080` | Structured compute dispatch |

`local-gpu` and `local-cpu` are two instances of the same `LocalExecutor` class with different configs. `openrouter` is an `OpenAICompatibleExecutor` instance. No subclassing needed for any of these.

`local-sidecar` is a new, thin executor type. It implements `ExecutorProtocol` but not `ReviewableExecutorProtocol`. For alpha, it needs only:
- `health()` — hit sidecar health endpoint, return stage + status
- `execute()` — dispatch a structured read-only task, return result

The sidecar executor is intentionally minimal. It proves routing dispatches non-LLM work to compute. It is not a distributed job framework.

### 2.3 LocalExecutor config updates

Update `LocalExecutorConfig` defaults:

```python
class LocalExecutorConfig(BaseModel):
    base_url: str = "http://172.16.0.109:8000"
    api_path: str = "/v3/chat/completions"
    models_path: str | None = None
    model: str = "Qwen2.5-7B-Instruct-INT4"
    executor_id: str = "local-gpu"
    timeout: float = 120.0
    max_tokens: int = 4096
    temperature: float = 0.0
    tier: ExecutorTier = ExecutorTier.LOCAL
    tags: list[str] = ["local", "a770", "gpu"]
    health_ttl: float = 60.0
```

The `LOCAL_EXECUTOR_URL` env override stays for flexibility.

Health probing when `models_path is None`: TCP connect to `{base_url}` with a short timeout. If the connection succeeds, report `ok`. Do not send a chat completions request as a health check — that burns inference tokens. The executor should not assume a `/models` endpoint exists.

Note: GPU.1 (port 8002, TinyLlama) is available on the A770 box but is not exercised in alpha. It can be added as a second fallback in `fallback_chain` later without architectural changes.

### 2.4 Routing policy

**Current problem:** `_find_ai_executor()` picks the first healthy general-purpose executor. `prefer_local` is a boolean. Every AI step gets the same executor.

**Fix:** A deterministic `RoutingPolicy` that maps step kinds and task tags to executor preferences. Routing is config-driven, not LLM-driven.

#### Data model

```python
class RoutingRule(BaseModel):
    step_kinds: list[StepKind] = []     # match on step kind
    tags: list[str] = []                # match on effective tags
    primary: str                        # executor_id to try first
    fallback_chain: list[str] = []      # ordered fallback executor_ids
    escalation_target: str | None = None
    escalation_triggers: list[EscalationTrigger] = []
    allow_escalation: bool = True
    fail_closed: bool = False           # if all options exhausted, stop (don't try others)

class EscalationTrigger(StrEnum):
    VERDICT_REJECT = "verdict_reject"
    SCHEMA_INVALID = "schema_invalid"
    RETRY_EXHAUSTED = "retry_exhausted"
    CONTEXT_EXCEEDED = "context_exceeded"

class RoutingPolicy(BaseModel):
    rules: list[RoutingRule]
    default_primary: str = "local-gpu"
    default_fallback: str = "openrouter"
```

Lives in `orchestration/routing.py`, alongside but separate from `budget.py`.

#### Precedence order

1. **Tag-based rules** — match if any rule tag is in the task's effective tags. These always win. `high_risk` and `write_path` force external regardless of step kind.
2. **Step-kind rules** — match on `StepKind` enum values only. No freeform labels.
3. **Global default** — `default_primary` with `default_fallback`.

#### Alpha routing table

```python
RoutingPolicy(rules=[
    # Tag overrides — always win
    RoutingRule(
        tags=["high_risk", "write_path"],
        primary="openrouter",
        fallback_chain=[],
        allow_escalation=False,
        fail_closed=True,           # if openrouter is down, stop. don't silently use local.
    ),

    # Inference: summary and review start local, can fall back and escalate
    RoutingRule(
        step_kinds=[StepKind.AI_SUMMARY, StepKind.AI_REVIEW],
        primary="local-gpu",
        fallback_chain=["local-cpu"],
        escalation_target="openrouter",
        escalation_triggers=[
            EscalationTrigger.VERDICT_REJECT,
            EscalationTrigger.SCHEMA_INVALID,
        ],
        allow_escalation=True,
    ),

    # Corrections need stronger reasoning
    RoutingRule(
        step_kinds=[StepKind.CORRECTION],
        primary="openrouter",
        fallback_chain=[],
        allow_escalation=False,
    ),

    # Compute tasks go to sidecar, no LLM fallback
    RoutingRule(
        step_kinds=[StepKind.COMPUTE_TASK],
        primary="local-sidecar",
        fallback_chain=[],
        allow_escalation=False,
        fail_closed=True,
    ),
])
```

#### Tags

Tags exist at two levels:
- **Run-level tags** — set on `WorkRequest` (e.g., `["write_path"]`)
- **Task-level tags** — set on individual `PlannedTask` or `TaskRecord`

Effective tags = run tags + task tags, merged at dispatch time. This requires adding `tags: list[str] = []` to `WorkRequest` and `TaskRecord`.

#### Runner integration

Two new methods replace `_find_ai_executor()`:

- `_route_ai_step(kind: StepKind, effective_tags: list[str]) -> RoutingDecision`
  Returns: `(primary, fallback_chain, escalation_target, matched_rule)`
- `_maybe_escalate(kind: StepKind, effective_tags: list[str], trigger: EscalationTrigger) -> ExecutorProtocol | None`
  Evaluates the matched rule's escalation config and returns the escalation target if allowed.

`_summarize()`, `_review()`, and `_correct()` call `_route_ai_step()` instead of `_find_ai_executor()`.

#### StepKind extension

Add `COMPUTE_TASK` to the existing `StepKind` enum:

```python
class StepKind(StrEnum):
    DOMAIN_CALL = "domain_call"
    AI_SUMMARY = "ai_summary"
    AI_REVIEW = "ai_review"
    CORRECTION = "correction"
    COMPUTE_TASK = "compute_task"    # new
```

### 2.5 Routing event logging

Every AI step emits a structured routing event via structlog:

```python
log.info(
    "routing.decision",
    step_kind=kind,
    effective_tags=tags,
    matched_rule=rule_index,       # which rule fired
    primary=decision.primary,
    fallback_chain=decision.fallback_chain,
    escalation_target=decision.escalation_target,
    selected_executor=actual_executor_id,
    dispatch_type="initial" | "fallback" | "escalated",
)
```

This is also captured in `StepRecord.selection` with the existing `ExecutorSelection` model, extended with:

```python
class ExecutorSelection(BaseModel):
    executor_id: str | None = None
    reason: SelectionReason
    candidates_considered: int = 0
    domain_matches: int = 0
    matched_rule: int | None = None       # new: index of routing rule that fired
    dispatch_type: str | None = None      # new: "initial", "fallback", "escalated"
    effective_tags: list[str] = []        # new: tags that influenced the decision
```

---

## 3. Alpha validation

### 3.1 Goal

Prove that the orchestration loop works end-to-end with real AI backends, and that routing uses the A770 as a multi-capability worker — not a single-function endpoint.

This alpha validates capability-aware routing on a single multi-role local node plus one external escalation backend. It does not attempt generalized distributed execution.

### 3.2 Three alpha paths

**Path 1: GPU inference (golden path)**

Proves the primary orchestration loop works with real inference:

1. `WorkRequest(domain="topology")` with topology data from `topologies/lab.json`
2. `TopologyExecutor` runs verification (domain task, no AI)
3. Summary routed to `local-gpu` per routing rule (AI_SUMMARY → primary: local-gpu)
4. Review routed to `local-gpu` per routing rule (AI_REVIEW → primary: local-gpu)
5. If review returns REJECT → escalates to `openrouter` (escalation trigger)
6. `RunRecord` shows routing decisions in every `StepRecord`

**Path 2: CPU fallback (degraded local inference)**

Proves the node doesn't become useless when GPU is busy or still loading:

1. Same topology `WorkRequest`, but `local-gpu` reports unhealthy (OVMS GPU.0 stopped)
2. Routing tries `local-gpu`, gets unhealthy, walks `fallback_chain` to `local-cpu`
3. Summary and review execute on TinyLlama (lower quality, but loop completes)
4. `StepRecord.selection` shows: `primary="local-gpu"`, `selected="local-cpu"`, `dispatch_type="fallback"`
5. This also validates the staged readiness behavior — CPU inference is available before GPU finishes loading

**Path 3: Sidecar compute dispatch**

Proves the node accepts non-LLM work through routing, not special-casing:

1. `WorkRequest` containing a `COMPUTE_TASK` step (e.g., "collect OVMS model status across all ports on this host")
2. Routed to `local-sidecar` per routing rule (COMPUTE_TASK → primary: local-sidecar)
3. Sidecar executes, returns structured result (JSON: which models loaded, which ports healthy)
4. `StepRecord` shows compute dispatch with no LLM involvement
5. If sidecar unhealthy → step fails closed. No silent fallback to an LLM.

The compute path is intentionally thin for alpha: structured dispatch, read-only execution, structured result, fail-closed behavior. Nothing more.

### 3.3 Test matrix

| Test | GPU | CPU | Sidecar | OpenRouter | What it proves |
|---|---|---|---|---|---|
| Golden path | up | — | — | standby | Normal routing works |
| GPU REJECT escalation | up | — | — | up | REJECT triggers external escalation |
| CPU fallback | down | up | — | standby | Degraded inference on same node |
| Full local down | down | down | — | up | External catches inference when local is gone |
| Compute dispatch | — | — | up | — | Non-LLM work routed to sidecar |
| Sidecar down | — | — | down | — | Fail closed, no silent LLM fallback |
| Budget exhaustion | up | — | — | — | Policy limits respected |

### 3.4 How to run

Integration tests under `tests/integration/` with `@pytest.mark.integration` markers. Skipped in CI. Run manually against live backends.

A thin CLI script in `scripts/alpha_run.py` for ad-hoc orchestration runs that print the `RunRecord` with routing decisions.

### 3.5 What alpha does NOT do

- No write-path tasks (no `interface_assign`, no config pushes)
- No LLM-assisted routing (routing is pure config lookup)
- No streaming
- No concurrent task execution
- No distributed job framework through the sidecar

---

## 4. Code changes summary

### New files

| File | What |
|---|---|
| `orchestration/routing.py` | `RoutingPolicy`, `RoutingRule`, `EscalationTrigger`, routing logic |
| `executorkit/sidecar.py` | `SidecarExecutor` — thin work executor for A770 sidecar |
| `tests/integration/test_alpha_routing.py` | Integration test suite for the three alpha paths |
| `scripts/alpha_run.py` | Ad-hoc CLI runner for alpha validation |

### Modified files

| File | What changes |
|---|---|
| `executorkit/openai_compat.py` | Add `api_path`, `models_path` to config. Update `_chat_completion()` and `health()` URL construction. |
| `executorkit/local.py` | Update defaults (origin, model, tags). Pass `api_path` and `models_path` through to inner executor. Handle `models_path=None` in health probe. |
| `orchestration/runner.py` | Replace `_find_ai_executor()` with `_route_ai_step()` and `_maybe_escalate()`. Accept `RoutingPolicy` in constructor. Emit routing events. |
| `storekit/models.py` | Add `matched_rule`, `dispatch_type`, `effective_tags` to `ExecutorSelection`. Add `COMPUTE_TASK` to `StepKind`. |
| `taskkit/models.py` | Add `tags: list[str] = []` to `TaskRecord`. |
| `plannerkit/models.py` | Add `tags: list[str] = []` to `WorkRequest` and `PlannedTask`. |
| `orchestration/budget.py` | No changes. Routing is separate from budget. |

### Not changed

| File | Why |
|---|---|
| `executorkit/mock.py` | Still works for unit tests |
| `executorkit/topology.py` | Domain executor, no routing changes needed |
| `executorkit/protocol.py` | Protocols unchanged — `SidecarExecutor` implements existing `ExecutorProtocol` |
| `registry/executor_registry.py` | Registry is executor-agnostic, no changes needed |
| `storekit/json_store.py` | Persistence layer unchanged |
| `reviewkit/models.py` | Review models unchanged |

---

## 5. Dependencies

- `httpx` — already in use
- `sshpass` — already installed (for interface_assign, not needed here)
- `OPENROUTER_API_KEY` env var — required for OpenRouter executor
- A770 box reachable at `172.16.0.109` — required for integration tests
- No new Python packages required
