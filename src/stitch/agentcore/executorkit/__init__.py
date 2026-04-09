"""executorkit — Executor protocol and capability descriptors.

Defines what executors must implement. No concrete executor implementations.
"""

from vos.agentcore.executorkit.protocol import (
    ExecutorCapability,
    ExecutorHealth,
    ExecutorProtocol,
)

__all__ = [
    "ExecutorCapability",
    "ExecutorHealth",
    "ExecutorProtocol",
]
