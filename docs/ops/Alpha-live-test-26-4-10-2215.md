# Alpha Live Integration Test — Ralph Loop

Run live integration tests against real backends. All tests are **read-only**.
Do NOT run write-path operations (no canary apply, no interface_assign with dry_run=false).

## Backends

- **A770 GPU** — `http://172.16.0.109:8000` (model: `qwen25-7b`, path: `/v3/chat/completions`)
- **A770 CPU** — `http://172.16.0.109:8001` (model: `tinyllama-cpu`, path: `/v3/chat/completions`)
- **A770 Sidecar** — `http://172.16.0.109:8080` (health + work dispatch)
- **OpenRouter** — `https://openrouter.ai` (API key in `~/.stitch/secrets.json`, path: `/api/v1/chat/completions`)

## Rules

- Run `uv run ruff check src/ tests/ && uv run pytest tests/ -v && uv run pyright src/` after any code changes
- Do NOT modify routing policy logic or executor architecture
- Do NOT run write-path tools (no interface_assign, no config pushes)
- Do NOT modify `~/.stitch/secrets.json`
- If a backend is unreachable, log it and move to the next test. Do not block.
- Record all findings in `docs/ops/alpha-live-results-2026-04-10.md`
- Commit findings at the end

## Phase 1 — Backend health probes

Verify all four backends respond before testing:

```bash
# GPU
curl -s http://172.16.0.109:8000/v3/models
# CPU
curl -s http://172.16.0.109:8001/v3/models
# Sidecar
curl -s http://172.16.0.109:8080/health
# OpenRouter (needs auth)
curl -s -H "Authorization: Bearer $(python3 -c 'import json; print(json.load(open("/home/emesix/.stitch/secrets.json"))["openrouter_api_key"])')" https://openrouter.ai/api/v1/models | head -c 200
```

Record which backends are up. Continue with whatever is available.

## Phase 2 — GPU golden path (real inference)

Run `uv run python scripts/alpha_run.py` (default scenario).

Expected: Domain execution completes, GPU summarizes, GPU reviews and approves.

Record:
- Did summary contain meaningful content?
- Did review produce valid structured JSON?
- What was the verdict?
- Latency per step

## Phase 3 — CPU summary fallback

Run `uv run python scripts/alpha_run.py --cpu-fallback`.

Expected: Routing falls to `local-cpu`. Summary may succeed (plain text). Review will likely fail (structured JSON too complex for TinyLlama).

Record:
- Did CPU produce a usable summary?
- What was the review error (if any)?
- Was `dispatch_type=fallback` correctly logged?

## Phase 4 — OpenRouter escalation

This is the first live test of OpenRouter. Write a small test script or extend `alpha_run.py`:

1. Register an OpenRouter executor:
   ```python
   from stitch.agentcore.executorkit.openai_compat import OpenAICompatibleExecutor, OpenAIExecutorConfig
   
   openrouter = OpenAICompatibleExecutor(OpenAIExecutorConfig(
       base_url="https://openrouter.ai",
       api_path="/api/v1/chat/completions",
       models_path="/api/v1/models",
       model="anthropic/claude-sonnet-4",
       api_key_env="OPENROUTER_API_KEY",
       executor_id="openrouter",
   ))
   ```

2. Test health check — does `/api/v1/models` respond?
3. Test a simple execution — send a summary task, get response
4. Test escalation scenario — run full orchestration with GPU primary, force a REJECT review (use MockExecutor for local-gpu that returns REJECT verdict), verify OpenRouter handles the escalation

Record:
- Did OpenRouter health check pass?
- Did OpenRouter produce a valid response?
- Did escalation routing work? (dispatch_type should show "escalated")
- Latency for OpenRouter vs local GPU
- Which model did OpenRouter actually use?

## Phase 5 — Sidecar compute dispatch

Test the sidecar executor against the live sidecar:

1. Check sidecar health: `curl -s http://172.16.0.109:8080/health`
2. Run a COMPUTE_TASK through the orchestrator with the sidecar registered
3. Verify routing selects `local-sidecar` for COMPUTE_TASK steps

If the sidecar API doesn't match what `SidecarExecutor` expects:
- Document the actual API shape
- Note what needs to change (but do NOT change executor code in this loop)

Record:
- Sidecar health response shape
- Did execute() succeed or fail?
- If failed, what was the actual API mismatch?

## Phase 6 — Full orchestration with all four executors

Register all four executors and run a topology WorkRequest:

- TopologyExecutor for domain tasks
- local-gpu for summary + review
- local-cpu as fallback (should not be needed if GPU is up)
- openrouter as escalation target + correction executor
- local-sidecar registered but no COMPUTE_TASK in this flow

Expected: Full plan → execute → summarize → review → (possibly correct) → complete.

Record:
- Total step count
- Which executor handled each step
- Did the full loop complete?
- Was the summary meaningful?
- Was the review verdict sensible?
- If correction happened, was OpenRouter used?

## Phase 7 — Write results

Create `docs/ops/alpha-live-results-2026-04-10.md` with:

1. Backend availability table
2. Per-phase results
3. Known issues / capability boundaries
4. Recommendations for next steps

Format:

```markdown
# Alpha Live Integration Results — 2026-04-10

## Backend Status
| Backend | URL | Status | Latency |
|---|---|---|---|

## Phase Results
### Phase N: [name]
**Result:** PASS / PARTIAL / FAIL
**Details:** ...

## Known Issues
- ...

## Recommendations
- ...
```

Commit the results file.

## Completion gate

When ALL phases have been attempted (some may fail — that's fine, record the failure) and results are written:

```
<promise>ALPHA LIVE TEST COMPLETE</promise>
```

If results are not yet written, do not output the promise. Write them first.
