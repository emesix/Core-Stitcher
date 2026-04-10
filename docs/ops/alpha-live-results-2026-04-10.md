# Alpha Live Integration Results — 2026-04-10

## Backend Status

| Backend | URL | Status | Model / Details | Latency |
|---|---|---|---|---|
| GPU (Qwen2.5-7B) | `172.16.0.109:8000` | UP | `qwen25-7b` (OVMS) | ~1s summary, ~4s review |
| CPU (TinyLlama) | `172.16.0.109:8001` | UP | `tinyllama-cpu` (OVMS) | <1s |
| Sidecar | `172.16.0.109:8080` | UP | ovms_gpu0/gpu1/cpu all ok | 185ms health |
| OpenRouter | `openrouter.ai` | UP | `anthropic/claude-sonnet-4` | 126ms health, 2-12s execute |

All four backends operational at test time.

## Phase Results

### Phase 1: Backend Health Probes

**Result:** PASS

All four backends responded successfully:
- GPU: `/v3/models` returned `qwen25-7b`
- CPU: `/v3/models` returned `tinyllama-cpu`
- Sidecar: `/health` returned `{status: "ok", details: {ovms_gpu0: "ok", ovms_gpu1: "ok", ovms_cpu: "ok"}}`
- OpenRouter: `/api/v1/models` returned model list (authenticated via secrets.json)

### Phase 2: GPU Golden Path

**Result:** PASS

Full orchestration loop completed with real GPU inference:
- Domain execution: completed (MockExecutor for topology)
- Summary (local-gpu, rule #1): Produced meaningful plain-text summary
- Review (local-gpu, rule #2): Produced valid structured JSON
  - First review: `request_changes` (noted mock data lacked specifics)
  - Correction skipped (openrouter not registered in this scenario)
  - Second review: `approve`
- Routing metadata correctly persisted: `matched_rule`, `dispatch_type=initial`, `effective_tags`
- structlog events emitted for each routing decision

### Phase 3: CPU Summary Fallback

**Result:** PASS

GPU not registered, routing correctly fell to CPU:
- Summary (local-cpu, rule #1, dispatch_type=**fallback**): Completed successfully
- Review (rule #2, **fail_closed**): Correctly blocked — CPU not in review fallback chain, openrouter not registered
- 3 skipped review steps (max_reviews loop) — minor: could break early on `policy_disallowed` in future
- Demonstrates staged readiness: CPU available even when GPU isn't

### Phase 4: OpenRouter Escalation

**Result:** PASS

- OpenRouter health: `ok` (126ms via `/api/v1/models`)
- OpenRouter execute: `completed` — Claude Sonnet responded correctly (2.0s latency)
- **API key issue found**: env var `OPENROUTER_API_KEY` in shell was stale (`sk-or-v1-22ab...`), while `~/.stitch/secrets.json` had the valid key (`sk-or-v1-d677...`). The secrets.json fallback resolved this once the env var was unset.
- Escalation scenario (mock local-gpu REJECT + real OpenRouter correction):
  - Summary: local-gpu (mock)
  - Review: local-gpu (mock REJECT)
  - Correction: **openrouter** (real Claude Sonnet, rule #3, produced meaningful correction)
  - Second correction cycle also completed via OpenRouter
  - Budget exhaustion correctly stopped after max_corrections=2
- Routing note: corrections route to OpenRouter as their *primary* (rule #3), not via the `_maybe_escalate()` path. The `escalation_triggers` on the review rule are available for explicit escalation but the current runner uses routing-as-correction, not escalation-as-retry.

### Phase 5: Sidecar Compute Dispatch

**Result:** PARTIAL

- Health check: **PASS** — `/health` returns `{status: "ok", details: {...}}`
  - SidecarExecutor reports "stage: unknown" (health response has `details` not `stage`)
- Execute: **FAIL** — API mismatch
  - SidecarExecutor POSTs to `/execute` — actual endpoint is `/work`
  - Request schema close but different: sidecar expects `{id: uuid, description: str, domain?, metadata}` (mirrors TaskRecord)
  - Response schema matches TaskOutcome: `{status, result, error, executor_id}`
  - Live `/work` endpoint works: tested shell command dispatch, returned `{exit_code, stdout, stderr, duration_ms}`

**API surface discovered:**

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Health report with OVMS backend details |
| `/capabilities` | GET | ExecutorCapability-shaped report |
| `/status` | GET | Full status |
| `/work` | POST | Shell command dispatch (read-only) |
| `/docs` | GET | Swagger UI |

### Phase 6: Full Orchestration (All Four Executors)

**Result:** PASS

All five executors registered (topo, local-gpu, local-cpu, openrouter, sidecar):

| Step | Kind | Status | Executor | Dispatch | Rule |
|---|---|---|---|---|---|
| 1 | domain_call | completed | topo-exec | — | — |
| 2 | ai_summary | completed | local-gpu | initial | #1 |
| 3 | ai_review | completed | local-gpu | initial | #2 |

- Summary: "The lab topology health check was verified, but no specific issues were reported." (90 chars)
- Review: `approve` on first attempt — valid structured JSON from qwen25-7b
- No correction needed (no REJECT)
- Sidecar registered but correctly not exercised (no COMPUTE_TASK)
- OpenRouter registered but correctly not exercised (no REJECT, no correction)
- Routing policy selected the right executor for each step kind

## Known Issues

1. **Stale env var**: `OPENROUTER_API_KEY` env var takes precedence over `~/.stitch/secrets.json` — if the env var is stale, OpenRouter calls fail with 401. Fix: unset env var or update it.

2. **Sidecar API mismatch**: `SidecarExecutor` POSTs to `/execute`, actual sidecar uses `/work`. Also, health response has `details` not `stage`. Need to align executor with real API.

3. **Review fail-closed loop**: When review is `fail_closed` and no executor available, the `max_reviews` loop runs all 3 iterations producing 3 identical SKIPPED steps. Could break early on `policy_disallowed`.

4. **No live escalation via `_maybe_escalate()`**: Corrections use `openrouter` as their routing *primary*, not the review rule's `escalation_target`. The `_maybe_escalate()` method exists but isn't called in the current runner feedback loop. This means `escalation_triggers` on review rules are unused at runtime — they're metadata only.

## Recommendations

1. **Fix sidecar executor**: Change `/execute` to `/work`, update health to read `details` instead of `stage`, align request payload with actual API (`id` required, `read_only`/`tags` not accepted).

2. **Wire `_maybe_escalate()`**: After a REJECT review verdict, call `_maybe_escalate(VERDICT_REJECT)` to try the escalation target *before* falling through to the correction step. This would exercise the escalation triggers and give the runner a two-phase quality recovery: escalate review first, then correct if needed.

3. **Break early on fail-closed**: In the review loop, if `_route_ai_step()` returns `policy_disallowed`, break immediately instead of looping `max_reviews` times.

4. **Resolve env var conflict**: Either remove stale `OPENROUTER_API_KEY` from shell profile, or make secrets.json take precedence over env vars (inverting current priority).

5. **Add real topology data**: Replace MockExecutor for topology with the real TopologyExecutor + lab.json to prove the full end-to-end path with real domain data.
