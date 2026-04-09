"""Tests for OpenAI-compatible executor with mocked HTTP transport."""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import httpx
import pytest

from stitch.agentcore.executorkit import ExecutorProtocol
from stitch.agentcore.executorkit.openai_compat import (
    OpenAICompatibleExecutor,
    OpenAIExecutorConfig,
)
from stitch.agentcore.registry import ExecutorRegistry
from stitch.agentcore.reviewkit import ReviewRequest, ReviewVerdict
from stitch.agentcore.taskkit import TaskRecord, TaskStatus


def _config(**overrides) -> OpenAIExecutorConfig:
    defaults = {"base_url": "http://fake:8080/v1", "api_key_env": "TEST_API_KEY"}
    return OpenAIExecutorConfig(**(defaults | overrides))


def _chat_response(content: str) -> dict:
    return {
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "model": "test",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
    }


def _patch_httpx(response_content: str, status_code: int = 200):
    class PatchedClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url: str, *, headers=None, json=None, **kwargs):
            return httpx.Response(
                status_code,
                json=_chat_response(response_content),
                request=httpx.Request("POST", url),
            )

        async def get(self, url: str, *, headers=None, **kwargs):
            return httpx.Response(
                200,
                json={"data": [{"id": "gpt-4o-mini"}]},
                request=httpx.Request("GET", url),
            )

    return patch("httpx.AsyncClient", PatchedClient)


# --- Protocol compliance ---


def test_implements_protocol():
    assert isinstance(OpenAICompatibleExecutor(_config()), ExecutorProtocol)


def test_executor_id():
    ex = OpenAICompatibleExecutor(_config(executor_id="my-openai"))
    assert ex.executor_id == "my-openai"


def test_capability_domains():
    ex = OpenAICompatibleExecutor(_config(domains=["topology", "research"]))
    assert ex.capability.domains == ["topology", "research"]


# --- Health ---


async def test_health_no_api_key():
    ex = OpenAICompatibleExecutor(_config(api_key_env="NONEXISTENT_KEY_12345"))
    h = await ex.health()
    assert h.status == "error"
    assert "not set" in h.message


async def test_health_ok():
    ex = OpenAICompatibleExecutor(_config())
    with patch.dict(os.environ, {"TEST_API_KEY": "sk-test"}), _patch_httpx("ok"):
        h = await ex.health()
    assert h.status == "ok"


# --- Execute ---


async def test_execute_success():
    ex = OpenAICompatibleExecutor(_config())
    task = TaskRecord(description="explain topology")

    with patch.dict(os.environ, {"TEST_API_KEY": "sk-test"}), _patch_httpx("Topology is..."):
        outcome = await ex.execute(task)

    assert outcome.status == TaskStatus.COMPLETED
    assert outcome.result == "Topology is..."
    assert outcome.executor_id == "openai-compat"
    assert outcome.started_at is not None
    assert outcome.finished_at is not None


async def test_execute_with_domain():
    ex = OpenAICompatibleExecutor(_config())
    task = TaskRecord(description="verify", domain="topology")

    with patch.dict(os.environ, {"TEST_API_KEY": "sk-test"}), _patch_httpx("verified"):
        outcome = await ex.execute(task)

    assert outcome.status == TaskStatus.COMPLETED


async def test_execute_with_metadata():
    ex = OpenAICompatibleExecutor(_config())
    task = TaskRecord(description="analyze", metadata={"source": "user"})

    with patch.dict(os.environ, {"TEST_API_KEY": "sk-test"}), _patch_httpx("done"):
        outcome = await ex.execute(task)

    assert outcome.status == TaskStatus.COMPLETED


async def test_execute_http_error():
    class FailClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, **kwargs):
            raise httpx.ConnectError("refused")

    ex = OpenAICompatibleExecutor(_config())
    task = TaskRecord(description="fail")

    env = patch.dict(os.environ, {"TEST_API_KEY": "sk-test"})
    with env, patch("httpx.AsyncClient", FailClient):
        outcome = await ex.execute(task)

    assert outcome.status == TaskStatus.FAILED
    assert "refused" in outcome.error


# --- Review ---


async def test_review_json_response():
    review_json = json.dumps({
        "verdict": "approve",
        "findings": [
            {"description": "looks good", "severity": "info", "category": "quality"},
        ],
        "summary": "all clear",
    })
    ex = OpenAICompatibleExecutor(_config())
    req = ReviewRequest(criteria=["correctness"])

    with patch.dict(os.environ, {"TEST_API_KEY": "sk-test"}), _patch_httpx(review_json):
        result = await ex.review(req)

    assert result.verdict == ReviewVerdict.APPROVE
    assert len(result.findings) == 1
    assert result.findings[0].category == "quality"
    assert result.summary == "all clear"


async def test_review_request_changes():
    review_json = json.dumps({
        "verdict": "request_changes",
        "findings": [
            {"description": "missing test", "severity": "error", "suggestion": "add test"},
        ],
        "summary": "needs work",
    })
    ex = OpenAICompatibleExecutor(_config())
    req = ReviewRequest(criteria=["completeness"])

    with patch.dict(os.environ, {"TEST_API_KEY": "sk-test"}), _patch_httpx(review_json):
        result = await ex.review(req)

    assert result.verdict == ReviewVerdict.REQUEST_CHANGES
    assert result.has_errors is True
    assert result.findings[0].suggestion == "add test"


async def test_review_non_json_response():
    ex = OpenAICompatibleExecutor(_config())
    req = ReviewRequest(criteria=["quality"])

    with patch.dict(os.environ, {"TEST_API_KEY": "sk-test"}), _patch_httpx("This looks fine"):
        result = await ex.review(req)

    assert result.verdict == ReviewVerdict.APPROVE
    assert len(result.findings) == 1
    assert "This looks fine" in result.findings[0].description


async def test_review_http_error():
    class FailClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, **kwargs):
            raise httpx.ConnectError("refused")

    ex = OpenAICompatibleExecutor(_config())
    req = ReviewRequest()

    env = patch.dict(os.environ, {"TEST_API_KEY": "sk-test"})
    with env, patch("httpx.AsyncClient", FailClient):
        result = await ex.review(req)

    assert result.verdict == ReviewVerdict.REQUEST_CHANGES
    assert result.has_errors is True


# --- Registry integration ---


async def test_registry_resolves_openai_executor():
    reg = ExecutorRegistry()
    ex = OpenAICompatibleExecutor(_config(executor_id="oai", domains=["topology"]))
    reg.register(ex)

    task = TaskRecord(description="verify", domain="topology")
    matches = reg.find_for_task(task)
    assert len(matches) == 1
    assert matches[0].executor_id == "oai"


# --- Opt-in real smoke test ---


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set — skipping real smoke test",
)
async def test_real_openai_smoke():
    """Real API call — only runs when OPENAI_API_KEY is set."""
    ex = OpenAICompatibleExecutor(OpenAIExecutorConfig(model="gpt-4o-mini"))
    h = await ex.health()
    assert h.status == "ok"

    task = TaskRecord(description="Say 'hello' and nothing else.")
    outcome = await ex.execute(task)
    assert outcome.status == TaskStatus.COMPLETED
    assert "hello" in outcome.result.lower()
