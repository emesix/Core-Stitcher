"""Shared fixtures for CLI tests."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from stitch.core.queries import QueryResult
from stitch.sdk.client import StitchClient


@pytest.fixture
def mock_client():
    client = AsyncMock(spec=StitchClient)
    client.query = AsyncMock(return_value=QueryResult(items=[], total=0))
    client.command = AsyncMock(return_value={})
    client.close = AsyncMock()
    return client
