"""App factory — wire store, registry, and routes into a FastAPI app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from vos.agentcore.executorkit.mock import MockExecutor
from vos.agentcore.registry import ExecutorRegistry
from vos.agentcore.storekit import JsonRunStore
from vos.apps.project_stitcher.api import create_router


def create_app(
    store_dir: str | Path = "~/.vos/project-stitcher/runs",
    executor_id: str = "mock-1",
) -> FastAPI:
    store = JsonRunStore(Path(store_dir).expanduser())
    registry = ExecutorRegistry()
    registry.register(MockExecutor(executor_id))

    app = FastAPI(title="VOS Project Explorer", version="0.1.0")
    app.include_router(create_router(store, registry))
    return app
