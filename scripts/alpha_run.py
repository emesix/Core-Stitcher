#!/usr/bin/env python3
"""Alpha routing validation — ad-hoc runner for manual testing.

Runs a small topology scenario against live backends and prints routing
decisions clearly. Shows which rule matched, which executor was selected,
and whether fallback or escalation occurred.

Usage:
    uv run python scripts/alpha_run.py
    uv run python scripts/alpha_run.py --gpu-only
    uv run python scripts/alpha_run.py --cpu-fallback
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from stitch.agentcore.executorkit.local import LocalExecutor, LocalExecutorConfig
from stitch.agentcore.executorkit.mock import MockExecutor
from stitch.agentcore.executorkit.sidecar import SidecarConfig, SidecarExecutor
from stitch.agentcore.orchestration import RunOrchestrator
from stitch.agentcore.orchestration.routing import alpha_routing_policy
from stitch.agentcore.plannerkit import WorkRequest, plan_request
from stitch.agentcore.registry import ExecutorRegistry
from stitch.agentcore.storekit import JsonRunStore, RunRecord, RunStatus

GPU_URL = "http://172.16.0.109:8000"
CPU_URL = "http://172.16.0.109:8001"
SIDECAR_URL = "http://172.16.0.109:8080"


def build_registry(*, gpu: bool = True, cpu: bool = True, sidecar: bool = True) -> ExecutorRegistry:
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo-exec", domains=["topology"]))

    if gpu:
        reg.register(
            LocalExecutor(
                LocalExecutorConfig(
                    base_url=GPU_URL,
                    executor_id="local-gpu",
                    tags=["local", "a770", "gpu"],
                )
            )
        )
    if cpu:
        reg.register(
            LocalExecutor(
                LocalExecutorConfig(
                    base_url=CPU_URL,
                    model="tinyllama-cpu",
                    executor_id="local-cpu",
                    tags=["local", "a770", "cpu"],
                )
            )
        )
    if sidecar:
        reg.register(SidecarExecutor(SidecarConfig(base_url=SIDECAR_URL)))

    return reg


def print_run_report(run: RunRecord) -> None:
    print(f"\n{'=' * 60}")
    print(f"Run: {run.run_id}")
    print(f"Status: {run.status}")
    print(f"Steps: {len(run.steps)}")
    print(f"{'=' * 60}\n")

    for i, step in enumerate(run.steps):
        sel = step.selection
        print(f"Step {i + 1}: {step.kind} — {step.status}")
        print(f"  Description: {step.description}")
        if sel:
            print(f"  Executor: {sel.executor_id or '(none)'}")
            print(f"  Reason: {sel.reason}")
            if sel.matched_rule is not None:
                print(f"  Matched rule: #{sel.matched_rule}")
            if sel.dispatch_type:
                print(f"  Dispatch type: {sel.dispatch_type}")
            if sel.effective_tags:
                print(f"  Effective tags: {sel.effective_tags}")
        if step.error:
            print(f"  Error: {step.error}")
        if step.result and isinstance(step.result, str) and len(step.result) < 200:
            print(f"  Result: {step.result}")
        print()

    if run.summary:
        print("Summary (first 200 chars):")
        print(f"  {run.summary[:200]}")
    if run.reviews:
        for r in run.reviews:
            print(f"Review: {r.verdict} — {r.summary[:100] if r.summary else ''}")
    print()


async def run_scenario(
    name: str,
    *,
    gpu: bool = True,
    cpu: bool = True,
    sidecar: bool = True,
    tags: list[str] | None = None,
) -> None:
    print(f"\n{'#' * 60}")
    print(f"# Scenario: {name}")
    print(f"# GPU={gpu}, CPU={cpu}, Sidecar={sidecar}")
    if tags:
        print(f"# Tags: {tags}")
    print(f"{'#' * 60}")

    store = JsonRunStore(Path("/tmp/alpha_runs"))
    reg = build_registry(gpu=gpu, cpu=cpu, sidecar=sidecar)
    routing = alpha_routing_policy()

    request = WorkRequest(
        description="Verify lab topology health",
        domain="topology",
        tags=tags or [],
    )
    plan = plan_request(request)
    run = RunRecord(status=RunStatus.PLANNED, request=request, plan=plan)
    store.save(run)

    orchestrator = RunOrchestrator(reg, store, routing=routing)

    try:
        result = await orchestrator.orchestrate(str(run.run_id))
        print_run_report(result)
    except Exception as e:
        print(f"\nError: {e}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Alpha routing validation")
    parser.add_argument("--gpu-only", action="store_true", help="GPU inference only")
    parser.add_argument("--cpu-fallback", action="store_true", help="Simulate GPU down")
    parser.add_argument("--all", action="store_true", help="Run all scenarios")
    args = parser.parse_args()

    if args.gpu_only:
        await run_scenario("GPU golden path", gpu=True, cpu=False, sidecar=False)
    elif args.cpu_fallback:
        await run_scenario("CPU fallback (GPU down)", gpu=False, cpu=True, sidecar=False)
    elif args.all:
        await run_scenario("GPU golden path", gpu=True, cpu=False, sidecar=False)
        await run_scenario("CPU fallback (GPU down)", gpu=False, cpu=True, sidecar=False)
        await run_scenario("Full local (GPU + CPU)", gpu=True, cpu=True, sidecar=False)
        await run_scenario("With sidecar", gpu=True, cpu=True, sidecar=True)
    else:
        # Default: golden path
        await run_scenario("GPU golden path (default)", gpu=True, cpu=False, sidecar=False)


if __name__ == "__main__":
    asyncio.run(main())
