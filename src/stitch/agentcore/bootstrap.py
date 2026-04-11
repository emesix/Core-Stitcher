"""Alpha bootstrap — build executor registry + routing for production use.

Assembles the real executor backends (TopologyExecutor, LocalExecutor,
OpenAICompatibleExecutor, SidecarExecutor) with the alpha routing policy.
Falls back to MockExecutor when STITCH_MOCK_EXECUTORS=1 or when no real
backends are configured.
"""

from __future__ import annotations

import os

import structlog

from stitch.agentcore.executorkit.local import LocalExecutor, LocalExecutorConfig
from stitch.agentcore.executorkit.mock import MockExecutor
from stitch.agentcore.executorkit.openai_compat import (
    OpenAICompatibleExecutor,
    OpenAIExecutorConfig,
)
from stitch.agentcore.executorkit.sidecar import SidecarConfig, SidecarExecutor
from stitch.agentcore.executorkit.topology import TopologyExecutor, TopologyExecutorConfig
from stitch.agentcore.orchestration.routing import RoutingPolicy, alpha_routing_policy
from stitch.agentcore.registry import ExecutorRegistry

log = structlog.get_logger()

GPU_URL = "http://172.16.0.109:8000"
CPU_URL = "http://172.16.0.109:8001"
SIDECAR_URL = "http://172.16.0.109:8080"


def build_alpha_registry() -> tuple[ExecutorRegistry, RoutingPolicy]:
    """Build the alpha executor registry with real backends.

    Returns (registry, routing_policy). If STITCH_MOCK_EXECUTORS=1,
    returns a mock-only registry with no routing policy.
    """
    if os.environ.get("STITCH_MOCK_EXECUTORS", "").strip() in ("1", "true"):
        log.info("bootstrap.mock_mode", reason="STITCH_MOCK_EXECUTORS set")
        return _build_mock_registry()

    registry = ExecutorRegistry()
    registered: list[str] = []

    # TopologyExecutor — domain="topology"
    registry.register(TopologyExecutor(TopologyExecutorConfig()))
    registered.append("topology-ruggensgraat")

    # LocalExecutor — local-gpu (INTELL-A770, Qwen2.5-7B)
    registry.register(
        LocalExecutor(
            LocalExecutorConfig(
                base_url=GPU_URL,
                executor_id="local-gpu",
                model="qwen25-7b",
                tags=["local", "a770", "gpu"],
            )
        )
    )
    registered.append("local-gpu")

    # LocalExecutor — local-cpu (TinyLlama CPU)
    registry.register(
        LocalExecutor(
            LocalExecutorConfig(
                base_url=CPU_URL,
                model="tinyllama-cpu",
                executor_id="local-cpu",
                tags=["local", "a770", "cpu"],
            )
        )
    )
    registered.append("local-cpu")

    # OpenAICompatibleExecutor — openrouter
    registry.register(
        OpenAICompatibleExecutor(
            OpenAIExecutorConfig(
                base_url="https://openrouter.ai",
                api_path="/api/v1/chat/completions",
                models_path="/api/v1/models",
                model="openai/gpt-4o-mini",
                api_key_env="OPENROUTER_API_KEY",
                executor_id="openrouter",
            )
        )
    )
    registered.append("openrouter")

    # SidecarExecutor — structured compute on A770
    registry.register(SidecarExecutor(SidecarConfig(base_url=SIDECAR_URL)))
    registered.append("local-sidecar")

    routing = alpha_routing_policy()
    log.info("bootstrap.alpha_ready", executors=registered)
    return registry, routing


def _build_mock_registry() -> tuple[ExecutorRegistry, RoutingPolicy]:
    """Fallback registry with MockExecutor only — for CI and testing."""
    registry = ExecutorRegistry()
    registry.register(MockExecutor("mock-1"))
    registry.register(MockExecutor("mock-topology", domains=["topology"]))
    # Return default routing policy pointing at mock IDs so orchestrator still works
    routing = RoutingPolicy(default_primary="mock-1", default_fallback="mock-1")
    return registry, routing
