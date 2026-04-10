"""Tests for configurable transport paths — api_path, models_path, TCP health."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx

from stitch.agentcore.executorkit.local import LocalExecutor, LocalExecutorConfig
from stitch.agentcore.executorkit.openai_compat import (
    OpenAICompatibleExecutor,
    OpenAIExecutorConfig,
)

# --- URL construction ---


def test_openai_config_defaults():
    cfg = OpenAIExecutorConfig()
    assert cfg.base_url == "https://api.openai.com"
    assert cfg.api_path == "/v1/chat/completions"
    assert cfg.models_path == "/v1/models"


def test_local_config_defaults():
    cfg = LocalExecutorConfig()
    assert cfg.base_url == "http://172.16.0.109:8000"
    assert cfg.api_path == "/v3/chat/completions"
    assert cfg.models_path is None
    assert cfg.model == "Qwen2.5-7B-Instruct-INT4"
    assert cfg.executor_id == "local-gpu"
    assert "gpu" in cfg.tags


def test_openrouter_config():
    cfg = OpenAIExecutorConfig(
        base_url="https://openrouter.ai",
        api_path="/api/v1/chat/completions",
        models_path="/api/v1/models",
    )
    assert f"{cfg.base_url}{cfg.api_path}" == "https://openrouter.ai/api/v1/chat/completions"
    assert f"{cfg.base_url}{cfg.models_path}" == "https://openrouter.ai/api/v1/models"


def test_ovms_config():
    cfg = LocalExecutorConfig(
        base_url="http://172.16.0.109:8000",
        api_path="/v3/chat/completions",
        models_path=None,
    )
    assert f"{cfg.base_url}{cfg.api_path}" == "http://172.16.0.109:8000/v3/chat/completions"
    assert cfg.models_path is None


# --- TCP health probe ---


async def test_tcp_health_ok():
    """TCP health probe succeeds when connection opens."""
    ex = OpenAICompatibleExecutor(
        OpenAIExecutorConfig(
            base_url="http://localhost:9999",
            models_path=None,
            api_key_env="TEST_KEY",
        )
    )

    mock_writer = AsyncMock()
    mock_writer.close = lambda: None
    mock_writer.wait_closed = AsyncMock()

    with (
        patch.dict("os.environ", {"TEST_KEY": "sk-test"}),
        patch(
            "asyncio.open_connection",
            return_value=(AsyncMock(), mock_writer),
        ),
    ):
        h = await ex.health()
    assert h.status == "ok"
    assert "tcp" in h.message


async def test_tcp_health_fail():
    """TCP health probe fails when connection refused."""
    ex = OpenAICompatibleExecutor(
        OpenAIExecutorConfig(
            base_url="http://localhost:9999",
            models_path=None,
            api_key_env="TEST_KEY",
        )
    )

    with (
        patch.dict("os.environ", {"TEST_KEY": "sk-test"}),
        patch(
            "asyncio.open_connection",
            side_effect=OSError("connection refused"),
        ),
    ):
        h = await ex.health()
    assert h.status == "error"
    assert "tcp" in h.message


async def test_tcp_health_timeout():
    """TCP health probe fails on timeout."""
    ex = OpenAICompatibleExecutor(
        OpenAIExecutorConfig(
            base_url="http://localhost:9999",
            models_path=None,
            api_key_env="TEST_KEY",
        )
    )

    with (
        patch.dict("os.environ", {"TEST_KEY": "sk-test"}),
        patch(
            "asyncio.open_connection",
            side_effect=TimeoutError("timed out"),
        ),
    ):
        h = await ex.health()
    assert h.status == "error"


# --- Local executor TCP health delegation ---


async def test_local_executor_tcp_health_when_models_path_none():
    """LocalExecutor delegates to TCP health when models_path is None."""
    cfg = LocalExecutorConfig(
        base_url="http://fake:8000",
        models_path=None,
    )
    ex = LocalExecutor(cfg)

    mock_writer = AsyncMock()
    mock_writer.close = lambda: None
    mock_writer.wait_closed = AsyncMock()

    with patch(
        "asyncio.open_connection",
        return_value=(AsyncMock(), mock_writer),
    ):
        h = await ex.health()
    assert h.status == "ok"
    assert ex.available is True


async def test_local_executor_http_health_when_models_path_set():
    """LocalExecutor uses HTTP health when models_path is set."""

    class PatchedClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url: str, **kwargs):
            return httpx.Response(
                200,
                json={"data": [{"id": "test-model"}]},
                request=httpx.Request("GET", url),
            )

    cfg = LocalExecutorConfig(
        base_url="http://fake:8000",
        models_path="/v1/models",
    )
    ex = LocalExecutor(cfg)

    with patch("httpx.AsyncClient", PatchedClient):
        h = await ex.health()
    assert h.status == "ok"
    assert ex.available is True
    assert "test-model" in ex.loaded_models


# --- Chat URL uses api_path ---


async def test_chat_url_uses_api_path():
    """Chat completions URL is built from base_url + api_path."""
    posted_urls: list[str] = []

    class CapturingClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url: str, *, headers=None, json=None, **kwargs):
            posted_urls.append(url)
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "ok"}}]},
                request=httpx.Request("POST", url),
            )

    cfg = OpenAIExecutorConfig(
        base_url="http://my-server:9000",
        api_path="/v3/chat/completions",
        api_key_env="TEST_KEY",
    )
    ex = OpenAICompatibleExecutor(cfg)

    from stitch.agentcore.taskkit.models import TaskRecord

    task = TaskRecord(description="test")

    with (
        patch.dict("os.environ", {"TEST_KEY": "sk-test"}),
        patch("httpx.AsyncClient", CapturingClient),
    ):
        await ex.execute(task)

    assert posted_urls == ["http://my-server:9000/v3/chat/completions"]
