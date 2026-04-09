# Phase 1: stitch-core + stitch-sdk + stitch-cli Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the operator layer foundation (core types, API client, CLI) so that `stitch device list`, `stitch preflight run --watch`, `stitch trace run 42 --from sw-core-01`, and `stitch run watch <id>` all work against the live lab.

**Architecture:** Three new packages within the existing monorepo: `stitch/core/` (pure types), `stitch/sdk/` (HTTP+WS client), `stitch/apps/operator/` (Typer CLI). The CLI calls the SDK, which calls the existing FastAPI endpoints. No changes to the domain layer — the operator layer is additive.

**Tech Stack:** Python 3.14, Typer, Rich, httpx (already dep), websockets (already dep), Pydantic v2

**Prerequisite:** Phase 0 (rename `vos` -> `stitch`) must be completed first. This plan assumes the rename has happened. All paths use `stitch.*` naming.

**Spec:** `docs/superpowers/specs/2026-04-09-stitch-operator-surface-design.md`

---

## File Structure

### New packages (operator layer)

```
src/stitch/core/
    __init__.py          — re-exports all public types
    resources.py         — Resource, ResourceURI (URI parsing + alias resolution)
    commands.py          — Command, CommandSpec, CommandSource, ExecutionMode, etc.
    queries.py           — Query, Filter, FilterOp, QueryResult
    streams.py           — StreamSubscription, StreamTopic, StreamEvent
    auth.py              — Session, Capability
    errors.py            — StitchError, TransportError, FieldError
    lifecycle.py         — LifecycleState, allowed transitions
    discovery.py         — SystemCapabilities, ResourceSpec, CommandSpec registry

src/stitch/sdk/
    __init__.py          — re-exports StitchClient
    client.py            — StitchClient (async, wraps all API calls)
    config.py            — StitchConfig, Profile, load_config()
    auth.py              — resolve_token(), build_headers()
    streaming.py         — StreamClient (WebSocket with reconnect + resume)
    endpoints.py         — endpoint mapping (stitch commands -> existing API paths)

src/stitch/apps/operator/
    __init__.py
    app.py               — Typer app, global flags/options, main()
    output.py            — OutputFormatter (human, json, table, compact, yaml)
    device.py            — stitch device {show,list,inspect}
    topology.py          — stitch topology {show,export,diff,diagnostics}
    preflight.py         — stitch preflight run [--watch]
    trace.py             — stitch trace {run,show,list}
    impact.py            — stitch impact {preview,show,list}
    run_cmds.py          — stitch run {create,show,list,watch,execute,cancel}
    review.py            — stitch review {request,show,list,approve,reject}
    report.py            — stitch report {show,list,diff}
    system.py            — stitch system {health,info,version}
    search.py            — stitch search
    show.py              — stitch show <uri>
```

### New test files

```
tests/stitch_core/
    test_resources.py
    test_queries.py
    test_commands.py
    test_streams.py
    test_errors.py
    test_lifecycle.py

tests/stitch_sdk/
    test_config.py
    test_client.py
    test_streaming.py
    test_endpoints.py
    test_auth.py

tests/stitch_cli/
    test_app.py
    test_output.py
    test_device.py
    test_preflight.py
    test_trace.py
    test_run.py
    conftest.py          — shared fixtures (mock client, test config)
```

### Modified files

```
pyproject.toml           — add typer, rich deps; add stitch console_scripts entry
```

---

## Task 1: Project Setup and Dependencies

**Files:**
- Modify: `pyproject.toml`
- Create: `src/stitch/core/__init__.py`
- Create: `src/stitch/sdk/__init__.py`
- Create: `src/stitch/apps/operator/__init__.py`

- [ ] **Step 1: Add dependencies to pyproject.toml**

```toml
# Add to [project.dependencies]:
# typer[all]>=0.15.0
# rich>=14.0.0
#
# Add to [project.scripts]:
# stitch = "stitch.apps.operator.app:main"
```

Open `pyproject.toml` and add `typer[all]>=0.15.0` and `rich>=14.0.0` to the dependencies list. Add the `stitch` console script entry point.

- [ ] **Step 2: Create package directories**

```bash
mkdir -p src/stitch/core src/stitch/sdk src/stitch/apps/operator
mkdir -p tests/stitch_core tests/stitch_sdk tests/stitch_cli
```

- [ ] **Step 3: Create minimal __init__.py files**

`src/stitch/core/__init__.py`:
```python
"""Stitch core types — pure data models, no IO."""
```

`src/stitch/sdk/__init__.py`:
```python
"""Stitch SDK — API client, stream client, auth."""
```

`src/stitch/apps/operator/__init__.py`:
```python
"""Stitch CLI — operator command-line interface."""
```

- [ ] **Step 4: Verify install**

Run: `uv pip install -e ".[dev]"`
Expected: Installs successfully with typer and rich available.

Run: `python -c "import typer; import rich; print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/stitch/ tests/stitch_core/ tests/stitch_sdk/ tests/stitch_cli/
git commit -m "feat(operator): scaffold stitch-core, stitch-sdk, stitch-cli packages"
```

---

## Task 2: Core Types — Errors, Lifecycle, Resources

**Files:**
- Create: `src/stitch/core/errors.py`
- Create: `src/stitch/core/lifecycle.py`
- Create: `src/stitch/core/resources.py`
- Test: `tests/stitch_core/test_errors.py`
- Test: `tests/stitch_core/test_lifecycle.py`
- Test: `tests/stitch_core/test_resources.py`

- [ ] **Step 1: Write failing tests for errors**

`tests/stitch_core/test_errors.py`:
```python
from stitch.core.errors import FieldError, StitchError, TransportError


def test_stitch_error_construction():
    err = StitchError(
        code="device.not_found",
        message="Device not found",
        retryable=False,
    )
    assert err.code == "device.not_found"
    assert err.retryable is False
    assert err.detail is None
    assert err.field_errors is None


def test_stitch_error_with_field_errors():
    err = StitchError(
        code="command.invalid_params",
        message="Invalid parameters",
        retryable=False,
        field_errors=[FieldError(field="vlan_id", code="required", message="VLAN ID is required")],
    )
    assert len(err.field_errors) == 1
    assert err.field_errors[0].field == "vlan_id"


def test_transport_error():
    err = TransportError(
        kind="timeout",
        message="Request timed out after 30s",
        retryable=True,
    )
    assert err.kind == "timeout"
    assert err.retryable is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/stitch_core/test_errors.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stitch.core.errors'`

- [ ] **Step 3: Implement errors.py**

`src/stitch/core/errors.py`:
```python
"""Shared error types across commands, queries, and streams."""

from __future__ import annotations

from pydantic import BaseModel


class FieldError(BaseModel):
    field: str
    code: str
    message: str


class StitchError(BaseModel):
    """Domain/protocol error returned by the server."""

    code: str
    message: str
    retryable: bool
    detail: dict | None = None
    correlation_id: str | None = None
    field_errors: list[FieldError] | None = None


class TransportError(BaseModel):
    """Transport-level failure (timeout, broken connection, gateway error)."""

    kind: str
    message: str
    retryable: bool
    detail: dict | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/stitch_core/test_errors.py -v`
Expected: 3 passed

- [ ] **Step 5: Write failing tests for lifecycle**

`tests/stitch_core/test_lifecycle.py`:
```python
import pytest

from stitch.core.lifecycle import LifecycleState, is_terminal, valid_transition


def test_lifecycle_states():
    assert LifecycleState.PENDING == "pending"
    assert LifecycleState.QUEUED == "queued"
    assert LifecycleState.RUNNING == "running"
    assert LifecycleState.SUCCEEDED == "succeeded"


def test_terminal_states():
    assert is_terminal(LifecycleState.SUCCEEDED) is True
    assert is_terminal(LifecycleState.FAILED) is True
    assert is_terminal(LifecycleState.CANCELLED) is True
    assert is_terminal(LifecycleState.TIMED_OUT) is True
    assert is_terminal(LifecycleState.RUNNING) is False
    assert is_terminal(LifecycleState.PENDING) is False


def test_valid_transitions():
    assert valid_transition(LifecycleState.PENDING, LifecycleState.QUEUED) is True
    assert valid_transition(LifecycleState.PENDING, LifecycleState.CANCELLED) is True
    assert valid_transition(LifecycleState.PENDING, LifecycleState.FAILED) is True
    assert valid_transition(LifecycleState.QUEUED, LifecycleState.RUNNING) is True
    assert valid_transition(LifecycleState.RUNNING, LifecycleState.SUCCEEDED) is True
    assert valid_transition(LifecycleState.RUNNING, LifecycleState.FAILED) is True
    assert valid_transition(LifecycleState.RUNNING, LifecycleState.CANCELLED) is True
    assert valid_transition(LifecycleState.RUNNING, LifecycleState.TIMED_OUT) is True


def test_invalid_transitions():
    assert valid_transition(LifecycleState.SUCCEEDED, LifecycleState.RUNNING) is False
    assert valid_transition(LifecycleState.FAILED, LifecycleState.PENDING) is False
    assert valid_transition(LifecycleState.PENDING, LifecycleState.SUCCEEDED) is False
```

- [ ] **Step 6: Implement lifecycle.py**

`src/stitch/core/lifecycle.py`:
```python
"""Lifecycle state machine for runs, tasks, reviews."""

from __future__ import annotations

from enum import StrEnum

_TERMINAL = frozenset({"succeeded", "failed", "cancelled", "timed_out"})

_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"queued", "cancelled", "failed"}),
    "queued": frozenset({"running", "cancelled"}),
    "running": frozenset({"succeeded", "failed", "cancelled", "timed_out"}),
}


class LifecycleState(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


def is_terminal(state: LifecycleState) -> bool:
    return state.value in _TERMINAL


def valid_transition(from_state: LifecycleState, to_state: LifecycleState) -> bool:
    allowed = _TRANSITIONS.get(from_state.value, frozenset())
    return to_state.value in allowed
```

- [ ] **Step 7: Run lifecycle tests**

Run: `uv run pytest tests/stitch_core/test_lifecycle.py -v`
Expected: 4 passed

- [ ] **Step 8: Write failing tests for resource URIs**

`tests/stitch_core/test_resources.py`:
```python
import pytest

from stitch.core.resources import Resource, ResourceURI, parse_uri


def test_parse_simple_uri():
    uri = parse_uri("stitch:/device/dev_01HX")
    assert uri.resource_type == "device"
    assert uri.resource_id == "dev_01HX"
    assert uri.sub_resource is None
    assert uri.sub_id is None


def test_parse_nested_uri():
    uri = parse_uri("stitch:/run/run_18f2/task/tsk_003F")
    assert uri.resource_type == "run"
    assert uri.resource_id == "run_18f2"
    assert uri.sub_resource == "task"
    assert uri.sub_id == "tsk_003F"


def test_parse_deep_uri():
    uri = parse_uri("stitch:/run/run_18f2/task/tsk_003F/step/stp_007Q")
    assert uri.resource_type == "run"
    assert uri.resource_id == "run_18f2"
    assert uri.sub_resource == "task"
    assert uri.sub_id == "tsk_003F"
    # deeper nesting preserved in extra_path
    assert uri.extra_path == "step/stp_007Q"


def test_uri_to_string():
    uri = ResourceURI(resource_type="device", resource_id="dev_01HX")
    assert str(uri) == "stitch:/device/dev_01HX"


def test_uri_to_string_nested():
    uri = ResourceURI(
        resource_type="run", resource_id="run_18f2",
        sub_resource="task", sub_id="tsk_003F",
    )
    assert str(uri) == "stitch:/run/run_18f2/task/tsk_003F"


def test_parse_invalid_uri():
    with pytest.raises(ValueError, match="Invalid stitch URI"):
        parse_uri("http://example.com")


def test_parse_bare_type():
    uri = parse_uri("stitch:/topology/current")
    assert uri.resource_type == "topology"
    assert uri.resource_id == "current"


def test_resource_model():
    res = Resource(
        uri="stitch:/device/dev_01HX",
        type="device",
        display_name="sw-core-01",
        summary="USW-Pro-48-PoE at 192.168.254.2",
    )
    assert res.display_name == "sw-core-01"
    assert res.status is None
    assert res.parent is None
```

- [ ] **Step 9: Implement resources.py**

`src/stitch/core/resources.py`:
```python
"""Resource identity — URIs, parsing, and the Resource summary type."""

from __future__ import annotations

import re

from pydantic import BaseModel

from stitch.core.lifecycle import LifecycleState

_URI_RE = re.compile(
    r"^stitch:/"
    r"(?P<type>[a-z_]+)/(?P<id>[^/]+)"
    r"(?:/(?P<sub_type>[a-z_]+)/(?P<sub_id>[^/]+))?"
    r"(?:/(?P<extra>.+))?$"
)


class ResourceURI(BaseModel):
    resource_type: str
    resource_id: str
    sub_resource: str | None = None
    sub_id: str | None = None
    extra_path: str | None = None

    def __str__(self) -> str:
        s = f"stitch:/{self.resource_type}/{self.resource_id}"
        if self.sub_resource and self.sub_id:
            s += f"/{self.sub_resource}/{self.sub_id}"
        if self.extra_path:
            s += f"/{self.extra_path}"
        return s


class Resource(BaseModel):
    """Navigable summary of any addressable entity."""

    uri: str
    type: str
    display_name: str
    summary: str
    status: LifecycleState | None = None
    parent: str | None = None
    children_hint: int | None = None


def parse_uri(uri: str) -> ResourceURI:
    m = _URI_RE.match(uri)
    if not m:
        msg = f"Invalid stitch URI: {uri}"
        raise ValueError(msg)
    return ResourceURI(
        resource_type=m.group("type"),
        resource_id=m.group("id"),
        sub_resource=m.group("sub_type"),
        sub_id=m.group("sub_id"),
        extra_path=m.group("extra"),
    )
```

- [ ] **Step 10: Run all core tests so far**

Run: `uv run pytest tests/stitch_core/ -v`
Expected: All passed

- [ ] **Step 11: Commit**

```bash
git add src/stitch/core/ tests/stitch_core/
git commit -m "feat(core): errors, lifecycle states, resource URI parsing"
```

---

## Task 3: Core Types — Queries, Commands, Streams

**Files:**
- Create: `src/stitch/core/queries.py`
- Create: `src/stitch/core/commands.py`
- Create: `src/stitch/core/streams.py`
- Create: `src/stitch/core/auth.py`
- Modify: `src/stitch/core/__init__.py`
- Test: `tests/stitch_core/test_queries.py`
- Test: `tests/stitch_core/test_commands.py`
- Test: `tests/stitch_core/test_streams.py`

- [ ] **Step 1: Write failing tests for queries**

`tests/stitch_core/test_queries.py`:
```python
from stitch.core.queries import Filter, FilterOp, Query, QueryResult, parse_filter


def test_query_minimal():
    q = Query(resource_type="device")
    assert q.resource_id is None
    assert q.filters == []
    assert q.cursor is None


def test_query_with_filters():
    q = Query(
        resource_type="device",
        filters=[Filter(field="type", op=FilterOp.EQ, value="SWITCH")],
        sort="-name",
        limit=10,
    )
    assert len(q.filters) == 1
    assert q.sort == "-name"


def test_query_result():
    qr = QueryResult(items=[{"uri": "stitch:/device/dev_01", "name": "sw-core-01"}], total=1)
    assert len(qr.items) == 1
    assert qr.next_cursor is None


def test_parse_filter_eq():
    f = parse_filter("type=SWITCH")
    assert f.field == "type"
    assert f.op == FilterOp.EQ
    assert f.value == "SWITCH"


def test_parse_filter_gte():
    f = parse_filter("severity>=WARNING")
    assert f.field == "severity"
    assert f.op == FilterOp.GTE
    assert f.value == "WARNING"


def test_parse_filter_contains():
    f = parse_filter("name~core")
    assert f.field == "name"
    assert f.op == FilterOp.CONTAINS
    assert f.value == "core"


def test_parse_filter_comma_values():
    f = parse_filter("status=PENDING,RUNNING")
    assert f.op == FilterOp.IN
    assert f.value == ["PENDING", "RUNNING"]


def test_parse_filter_neq():
    f = parse_filter("status!=CANCELLED")
    assert f.field == "status"
    assert f.op == FilterOp.NEQ
    assert f.value == "CANCELLED"
```

- [ ] **Step 2: Implement queries.py**

`src/stitch/core/queries.py`:
```python
"""Query model — read-only requests with filtering and pagination."""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, Field

_FILTER_RE = re.compile(
    r"^(?P<field>[a-z_]+)"
    r"(?P<op>!=|>=|<=|>|<|~|=)"
    r"(?P<value>.+)$"
)


class FilterOp(StrEnum):
    EQ = "="
    NEQ = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    CONTAINS = "~"
    IN = "in"


class Filter(BaseModel):
    field: str
    op: FilterOp
    value: str | list[str]


class Query(BaseModel):
    resource_type: str
    resource_id: str | None = None
    filters: list[Filter] = Field(default_factory=list)
    sort: str | None = None
    limit: int | None = None
    cursor: str | None = None
    fields: list[str] | None = None


class QueryResult(BaseModel):
    items: list[dict]
    total: int | None = None
    next_cursor: str | None = None


def parse_filter(text: str) -> Filter:
    """Parse a CLI filter string like 'type=SWITCH' or 'severity>=WARNING'."""
    m = _FILTER_RE.match(text)
    if not m:
        msg = f"Invalid filter: {text}"
        raise ValueError(msg)

    field = m.group("field")
    op_str = m.group("op")
    value_str = m.group("value")

    # Comma-separated values with = become IN
    if op_str == "=" and "," in value_str:
        return Filter(field=field, op=FilterOp.IN, value=value_str.split(","))

    op = FilterOp(op_str)
    return Filter(field=field, op=op, value=value_str)
```

- [ ] **Step 3: Run query tests**

Run: `uv run pytest tests/stitch_core/test_queries.py -v`
Expected: All passed

- [ ] **Step 4: Write failing tests for commands**

`tests/stitch_core/test_commands.py`:
```python
from stitch.core.commands import (
    Command,
    CommandSource,
    ExecutionMode,
    InteractionClass,
    RiskLevel,
)


def test_command_construction():
    cmd = Command(
        action="preflight.run",
        target="stitch:/topology/current",
        params={"scope": "site-rdam"},
        source=CommandSource.CLI,
        correlation_id="abc123",
    )
    assert cmd.action == "preflight.run"
    assert cmd.idempotency_key is None


def test_command_source_values():
    assert CommandSource.CLI == "cli"
    assert CommandSource.TUI == "tui"
    assert CommandSource.SCRIPT == "script"


def test_execution_mode():
    assert ExecutionMode.SYNC == "sync"
    assert ExecutionMode.ASYNC == "async"


def test_risk_level():
    assert RiskLevel.LOW == "low"
    assert RiskLevel.HIGH == "high"


def test_interaction_class():
    assert InteractionClass.NONE == "none"
    assert InteractionClass.CONFIRM == "confirm"
```

- [ ] **Step 5: Implement commands.py**

`src/stitch/core/commands.py`:
```python
"""Command model — state-changing actions."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class CommandSource(StrEnum):
    CLI = "cli"
    TUI = "tui"
    WEB = "web"
    LITE = "lite"
    DESKTOP = "desktop"
    API = "api"
    SCRIPT = "script"
    INTERNAL = "internal"


class ExecutionMode(StrEnum):
    SYNC = "sync"
    ASYNC = "async"


class InteractionClass(StrEnum):
    NONE = "none"
    CONFIRM = "confirm"
    FORM = "form"
    WIZARD = "wizard"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Command(BaseModel):
    action: str
    target: str | None = None
    params: dict[str, Any] = {}
    source: CommandSource = CommandSource.CLI
    correlation_id: str = ""
    idempotency_key: str | None = None
```

- [ ] **Step 6: Write and implement streams.py and auth.py**

`src/stitch/core/streams.py`:
```python
"""Stream model — live event subscriptions."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from stitch.core.queries import Filter


class StreamTopic(StrEnum):
    RUN_PROGRESS = "run.progress"
    RUN_LOG = "run.log"
    TASK_STATUS = "task.status"
    REVIEW_VERDICT = "review.verdict"
    MODULE_HEALTH = "module.health"
    TOPOLOGY_CHANGE = "topology.change"
    SYSTEM_EVENT = "system.event"


class StreamSubscription(BaseModel):
    topic: StreamTopic
    target: str | None = None
    filters: list[Filter] = []
    last_event_id: str | None = None


class StreamEvent(BaseModel):
    event_id: str
    sequence: int
    topic: StreamTopic
    resource: str
    payload: dict[str, Any]
    timestamp: datetime
    correlation_id: str | None = None
```

`src/stitch/core/auth.py`:
```python
"""Auth and session types."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from stitch.core.commands import CommandSource


class Capability(StrEnum):
    TOPOLOGY_READ = "topology.read"
    PREFLIGHT_RUN = "preflight.run"
    TRACE_RUN = "trace.run"
    IMPACT_RUN = "impact.run"
    RUNS_MANAGE = "runs.manage"
    RUNS_REVIEW = "runs.review"
    CHANGES_APPROVE = "changes.approve"
    LOGS_VIEW = "logs.view"
    ADMIN = "admin"


class Session(BaseModel):
    session_id: str
    user: str
    capabilities: set[str]
    scopes: dict[str, list[str]] | None = None
    client: CommandSource
    created_at: datetime
    expires_at: datetime | None = None
```

`tests/stitch_core/test_streams.py`:
```python
from datetime import datetime, timezone

from stitch.core.streams import StreamEvent, StreamSubscription, StreamTopic


def test_stream_subscription():
    sub = StreamSubscription(
        topic=StreamTopic.RUN_PROGRESS,
        target="stitch:/run/run_18f2",
    )
    assert sub.topic == "run.progress"
    assert sub.filters == []


def test_stream_event():
    evt = StreamEvent(
        event_id="evt_001",
        sequence=1,
        topic=StreamTopic.RUN_PROGRESS,
        resource="stitch:/run/run_18f2/task/tsk_001",
        payload={"status": "succeeded"},
        timestamp=datetime.now(timezone.utc),
    )
    assert evt.sequence == 1
    assert evt.payload["status"] == "succeeded"
```

- [ ] **Step 7: Update core __init__.py with re-exports**

`src/stitch/core/__init__.py`:
```python
"""Stitch core types — pure data models, no IO."""

from stitch.core.auth import Capability, Session
from stitch.core.commands import (
    Command,
    CommandSource,
    ExecutionMode,
    InteractionClass,
    RiskLevel,
)
from stitch.core.errors import FieldError, StitchError, TransportError
from stitch.core.lifecycle import LifecycleState, is_terminal, valid_transition
from stitch.core.queries import Filter, FilterOp, Query, QueryResult, parse_filter
from stitch.core.resources import Resource, ResourceURI, parse_uri
from stitch.core.streams import StreamEvent, StreamSubscription, StreamTopic

__all__ = [
    "Capability",
    "Command",
    "CommandSource",
    "ExecutionMode",
    "FieldError",
    "Filter",
    "FilterOp",
    "InteractionClass",
    "LifecycleState",
    "Query",
    "QueryResult",
    "Resource",
    "ResourceURI",
    "RiskLevel",
    "Session",
    "StitchError",
    "StreamEvent",
    "StreamSubscription",
    "StreamTopic",
    "TransportError",
    "is_terminal",
    "parse_filter",
    "parse_uri",
    "valid_transition",
]
```

- [ ] **Step 8: Run all core tests**

Run: `uv run pytest tests/stitch_core/ -v`
Expected: All passed

- [ ] **Step 9: Commit**

```bash
git add src/stitch/core/ tests/stitch_core/
git commit -m "feat(core): query, command, stream, and auth types"
```

---

## Task 4: SDK — Config and Auth

**Files:**
- Create: `src/stitch/sdk/config.py`
- Create: `src/stitch/sdk/auth.py`
- Test: `tests/stitch_sdk/test_config.py`
- Test: `tests/stitch_sdk/test_auth.py`

- [ ] **Step 1: Write failing tests for config**

`tests/stitch_sdk/test_config.py`:
```python
import pytest

from stitch.sdk.config import Profile, StitchConfig, load_config


def test_config_from_dict():
    cfg = StitchConfig(
        default_profile="lab",
        profiles={
            "lab": Profile(server="https://stitch.lab.local:8443", token="dev-token"),
        },
    )
    assert cfg.default_profile == "lab"
    assert cfg.profiles["lab"].server == "https://stitch.lab.local:8443"


def test_resolve_profile_explicit():
    cfg = StitchConfig(
        default_profile="lab",
        profiles={
            "lab": Profile(server="http://localhost:8000", token="lab-tok"),
            "prod": Profile(server="https://prod:8443", token="prod-tok"),
        },
    )
    p = cfg.resolve_profile("prod")
    assert p.server == "https://prod:8443"


def test_resolve_profile_default():
    cfg = StitchConfig(
        default_profile="lab",
        profiles={"lab": Profile(server="http://localhost:8000", token="t")},
    )
    p = cfg.resolve_profile(None)
    assert p.server == "http://localhost:8000"


def test_resolve_profile_missing():
    cfg = StitchConfig(default_profile="lab", profiles={})
    with pytest.raises(KeyError):
        cfg.resolve_profile("lab")


def test_load_config_from_yaml(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("""
default_profile: test
profiles:
  test:
    server: http://localhost:9000
    token: test-token
defaults:
  output: json
  page_size: 25
""")
    cfg = load_config(cfg_file)
    assert cfg.default_profile == "test"
    assert cfg.profiles["test"].token == "test-token"
    assert cfg.defaults.output == "json"
    assert cfg.defaults.page_size == 25


def test_load_config_missing_file():
    """Missing config file returns sensible defaults."""
    from pathlib import Path

    cfg = load_config(Path("/nonexistent/config.yaml"))
    assert cfg.default_profile is None
    assert cfg.profiles == {}


def test_profile_token_command(tmp_path):
    p = Profile(server="http://localhost:8000", token_command="echo secret-tok")
    tok = p.resolve_token()
    assert tok == "secret-tok"


def test_profile_token_direct():
    p = Profile(server="http://localhost:8000", token="direct-tok")
    tok = p.resolve_token()
    assert tok == "direct-tok"
```

- [ ] **Step 2: Implement config.py**

`src/stitch/sdk/config.py`:
```python
"""Stitch SDK configuration — profiles, server, token resolution."""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

_DEFAULT_CONFIG_PATH = Path.home() / ".config" / "stitch" / "config.yaml"


class Defaults(BaseModel):
    output: str = "human"
    color: str = "auto"
    confirm: bool = True
    page_size: int = 50


class Profile(BaseModel):
    server: str
    token: str | None = None
    token_command: str | None = None

    def resolve_token(self) -> str | None:
        """Resolve token: direct value or shell command."""
        if self.token:
            return self.token
        if self.token_command:
            result = subprocess.run(
                self.token_command,
                shell=True,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        return None


class StitchConfig(BaseModel):
    default_profile: str | None = None
    profiles: dict[str, Profile] = Field(default_factory=dict)
    defaults: Defaults = Field(default_factory=Defaults)

    def resolve_profile(self, name: str | None) -> Profile:
        """Resolve profile by name, falling back to default."""
        key = name or self.default_profile
        if key is None or key not in self.profiles:
            msg = f"Profile not found: {key}"
            raise KeyError(msg)
        return self.profiles[key]


def load_config(path: Path | None = None) -> StitchConfig:
    """Load config from YAML file. Returns defaults if file doesn't exist."""
    cfg_path = path or _DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        return StitchConfig()
    raw = yaml.safe_load(cfg_path.read_text()) or {}
    return StitchConfig(**raw)
```

- [ ] **Step 3: Run config tests**

Run: `uv run pytest tests/stitch_sdk/test_config.py -v`
Expected: All passed

- [ ] **Step 4: Write and implement auth.py**

`tests/stitch_sdk/test_auth.py`:
```python
import os

from stitch.sdk.auth import resolve_auth
from stitch.sdk.config import Profile


def test_resolve_auth_from_profile():
    p = Profile(server="http://localhost:8000", token="tok123")
    headers = resolve_auth(p)
    assert headers["Authorization"] == "Bearer tok123"


def test_resolve_auth_no_token():
    p = Profile(server="http://localhost:8000")
    headers = resolve_auth(p)
    assert "Authorization" not in headers


def test_resolve_auth_env_override(monkeypatch):
    monkeypatch.setenv("STITCH_TOKEN", "env-tok")
    p = Profile(server="http://localhost:8000", token="profile-tok")
    headers = resolve_auth(p, env_token=os.environ.get("STITCH_TOKEN"))
    assert headers["Authorization"] == "Bearer env-tok"
```

`src/stitch/sdk/auth.py`:
```python
"""Auth header resolution."""

from __future__ import annotations

from stitch.sdk.config import Profile


def resolve_auth(profile: Profile, env_token: str | None = None) -> dict[str, str]:
    """Build auth headers. env_token (STITCH_TOKEN) takes precedence."""
    token = env_token or profile.resolve_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}
```

- [ ] **Step 5: Run all SDK tests**

Run: `uv run pytest tests/stitch_sdk/ -v`
Expected: All passed

- [ ] **Step 6: Commit**

```bash
git add src/stitch/sdk/ tests/stitch_sdk/
git commit -m "feat(sdk): config loading, profile resolution, auth headers"
```

---

## Task 5: SDK — HTTP Client and Endpoint Mapping

**Files:**
- Create: `src/stitch/sdk/endpoints.py`
- Create: `src/stitch/sdk/client.py`
- Modify: `src/stitch/sdk/__init__.py`
- Test: `tests/stitch_sdk/test_endpoints.py`
- Test: `tests/stitch_sdk/test_client.py`

- [ ] **Step 1: Write failing tests for endpoint mapping**

`tests/stitch_sdk/test_endpoints.py`:
```python
from stitch.sdk.endpoints import resolve_endpoint


def test_device_list():
    method, path = resolve_endpoint("device", "list")
    assert method == "GET"
    assert path == "/explorer/devices"


def test_device_show():
    method, path = resolve_endpoint("device", "show", resource_id="dev_01HX")
    assert method == "GET"
    assert path == "/explorer/devices/dev_01HX"


def test_device_neighbors():
    method, path = resolve_endpoint("device", "neighbors", resource_id="dev_01HX")
    assert method == "GET"
    assert path == "/explorer/devices/dev_01HX/neighbors"


def test_topology_show():
    method, path = resolve_endpoint("topology", "show")
    assert method == "GET"
    assert path == "/explorer/topology"


def test_diagnostics():
    method, path = resolve_endpoint("topology", "diagnostics")
    assert method == "GET"
    assert path == "/explorer/diagnostics"


def test_vlan_show():
    method, path = resolve_endpoint("vlan", "show", resource_id="42")
    assert method == "GET"
    assert path == "/explorer/vlans/42"


def test_preflight_run():
    method, path = resolve_endpoint("preflight", "run")
    assert method == "POST"
    assert path == "/verify"


def test_trace_run():
    method, path = resolve_endpoint("trace", "run")
    assert method == "POST"
    assert path == "/trace"


def test_impact_preview():
    method, path = resolve_endpoint("impact", "preview")
    assert method == "POST"
    assert path == "/impact"


def test_run_list():
    method, path = resolve_endpoint("run", "list")
    assert method == "GET"
    assert path == "/runs"


def test_run_show():
    method, path = resolve_endpoint("run", "show", resource_id="run_18f2")
    assert method == "GET"
    assert path == "/runs/run_18f2"


def test_run_execute():
    method, path = resolve_endpoint("run", "execute", resource_id="run_18f2")
    assert method == "POST"
    assert path == "/runs/run_18f2/execute"


def test_system_health():
    method, path = resolve_endpoint("system", "health")
    assert method == "GET"
    assert path == "/api/v1/health"
```

- [ ] **Step 2: Implement endpoints.py**

`src/stitch/sdk/endpoints.py`:
```python
"""Map stitch commands to existing API endpoints."""

from __future__ import annotations

# (resource_type, verb) -> (HTTP_method, path_template)
# {id} is replaced with resource_id at resolve time.

_ENDPOINTS: dict[tuple[str, str], tuple[str, str]] = {
    # Explorer / topology browsing
    ("device", "list"): ("GET", "/explorer/devices"),
    ("device", "show"): ("GET", "/explorer/devices/{id}"),
    ("device", "neighbors"): ("GET", "/explorer/devices/{id}/neighbors"),
    ("topology", "show"): ("GET", "/explorer/topology"),
    ("topology", "diagnostics"): ("GET", "/explorer/diagnostics"),
    ("vlan", "show"): ("GET", "/explorer/vlans/{id}"),
    # Preflight / verification
    ("preflight", "run"): ("POST", "/verify"),
    ("trace", "run"): ("POST", "/trace"),
    ("impact", "preview"): ("POST", "/impact"),
    ("topology", "diff"): ("POST", "/diff"),
    # Orchestration runs
    ("run", "list"): ("GET", "/runs"),
    ("run", "show"): ("GET", "/runs/{id}"),
    ("run", "create"): ("POST", "/runs"),
    ("run", "execute"): ("POST", "/runs/{id}/execute"),
    ("run", "review"): ("POST", "/runs/{id}/review"),
    ("run", "orchestrate"): ("POST", "/runs/{id}/orchestrate"),
    # System
    ("system", "health"): ("GET", "/api/v1/health"),
    ("system", "info"): ("GET", "/api/v1/readyz"),
    ("system", "version"): ("GET", "/api/v1/livez"),
    # Module
    ("module", "list"): ("GET", "/api/v1/modules"),
    ("module", "health"): ("GET", "/health/modules"),
}


def resolve_endpoint(
    resource_type: str,
    verb: str,
    resource_id: str | None = None,
) -> tuple[str, str]:
    """Resolve a stitch command to (HTTP_method, URL_path)."""
    key = (resource_type, verb)
    if key not in _ENDPOINTS:
        msg = f"No endpoint for {resource_type}.{verb}"
        raise KeyError(msg)
    method, template = _ENDPOINTS[key]
    path = template.replace("{id}", resource_id or "")
    return method, path
```

- [ ] **Step 3: Run endpoint tests**

Run: `uv run pytest tests/stitch_sdk/test_endpoints.py -v`
Expected: All passed

- [ ] **Step 4: Write failing tests for the HTTP client**

`tests/stitch_sdk/test_client.py`:
```python
import json

import httpx
import pytest

from stitch.core.errors import StitchError, TransportError
from stitch.sdk.client import StitchClient
from stitch.sdk.config import Profile


@pytest.fixture
def profile():
    return Profile(server="http://testserver:8000", token="test-token")


@pytest.fixture
def mock_transport():
    """httpx mock transport for testing without network."""
    responses = {}

    class MockTransport(httpx.MockTransport):
        pass

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path in responses:
            status, body = responses[path]
            return httpx.Response(status, json=body)
        return httpx.Response(404, json={"detail": "Not found"})

    transport = MockTransport(handler)
    transport._responses = responses  # noqa: SLF001
    return transport


@pytest.mark.asyncio
async def test_client_query(profile, mock_transport):
    mock_transport._responses["/explorer/devices"] = (200, [
        {"id": "dev_01", "name": "sw-core-01", "type": "SWITCH"},
        {"id": "dev_02", "name": "sw-edge-01", "type": "SWITCH"},
    ])
    client = StitchClient(profile, transport=mock_transport)
    result = await client.query("device", "list")
    assert len(result.items) == 2
    assert result.items[0]["name"] == "sw-core-01"
    await client.close()


@pytest.mark.asyncio
async def test_client_query_single(profile, mock_transport):
    mock_transport._responses["/explorer/devices/dev_01"] = (200, {
        "id": "dev_01", "name": "sw-core-01", "type": "SWITCH", "ports": [],
    })
    client = StitchClient(profile, transport=mock_transport)
    result = await client.query("device", "show", resource_id="dev_01")
    assert result.items[0]["name"] == "sw-core-01"
    assert result.total == 1
    await client.close()


@pytest.mark.asyncio
async def test_client_command(profile, mock_transport):
    mock_transport._responses["/trace"] = (200, {
        "vlan": 42, "status": "complete", "hops": [],
    })
    client = StitchClient(profile, transport=mock_transport)
    result = await client.command("trace", "run", params={"vlan": 42, "source": "sw-core-01"})
    assert result["status"] == "complete"
    await client.close()


@pytest.mark.asyncio
async def test_client_auth_header(profile, mock_transport):
    """Verify that the client sends the auth header."""
    captured_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.update(dict(request.headers))
        return httpx.Response(200, json=[])

    transport = httpx.MockTransport(handler)
    client = StitchClient(profile, transport=transport)
    await client.query("device", "list")
    assert captured_headers.get("authorization") == "Bearer test-token"
    await client.close()


@pytest.mark.asyncio
async def test_client_server_error(profile, mock_transport):
    mock_transport._responses["/explorer/devices"] = (500, {
        "code": "system.unavailable",
        "message": "Internal error",
        "retryable": True,
    })
    client = StitchClient(profile, transport=mock_transport)
    with pytest.raises(StitchError, match="Internal error"):
        await client.query("device", "list")
    await client.close()
```

- [ ] **Step 5: Implement client.py**

`src/stitch/sdk/client.py`:
```python
"""Stitch API client — async HTTP with auth."""

from __future__ import annotations

import os
from typing import Any

import httpx

from stitch.core.errors import StitchError, TransportError
from stitch.core.queries import QueryResult
from stitch.sdk.auth import resolve_auth
from stitch.sdk.config import Profile
from stitch.sdk.endpoints import resolve_endpoint


class StitchClient:
    """Async HTTP client for the Stitch API."""

    def __init__(
        self,
        profile: Profile,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._profile = profile
        headers = resolve_auth(profile, env_token=os.environ.get("STITCH_TOKEN"))
        self._http = httpx.AsyncClient(
            base_url=profile.server,
            headers=headers,
            transport=transport,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def query(
        self,
        resource_type: str,
        verb: str,
        resource_id: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> QueryResult:
        """Execute a read-only query, return structured result."""
        method, path = resolve_endpoint(resource_type, verb, resource_id)
        response = await self._http.request(method, path, params=params)
        self._check_response(response)

        data = response.json()
        if isinstance(data, list):
            return QueryResult(items=data, total=len(data))
        return QueryResult(items=[data], total=1)

    async def command(
        self,
        resource_type: str,
        verb: str,
        resource_id: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a state-changing command, return raw result."""
        method, path = resolve_endpoint(resource_type, verb, resource_id)
        response = await self._http.request(method, path, json=params)
        self._check_response(response)
        return response.json()

    def _check_response(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            try:
                body = response.json()
                raise StitchError(
                    code=body.get("code", f"http.{response.status_code}"),
                    message=body.get("message", body.get("detail", "Unknown error")),
                    retryable=body.get("retryable", response.status_code >= 500),
                )
            except (ValueError, KeyError):
                raise TransportError(
                    kind="http_error",
                    message=f"HTTP {response.status_code}",
                    retryable=response.status_code >= 500,
                )
```

- [ ] **Step 6: Update SDK __init__.py**

`src/stitch/sdk/__init__.py`:
```python
"""Stitch SDK — API client, stream client, auth."""

from stitch.sdk.client import StitchClient
from stitch.sdk.config import StitchConfig, load_config

__all__ = ["StitchClient", "StitchConfig", "load_config"]
```

- [ ] **Step 7: Run all SDK tests**

Run: `uv run pytest tests/stitch_sdk/ -v`
Expected: All passed

- [ ] **Step 8: Commit**

```bash
git add src/stitch/sdk/ tests/stitch_sdk/
git commit -m "feat(sdk): HTTP client with endpoint mapping and auth"
```

---

## Task 6: CLI Scaffold and Output Formatters

**Files:**
- Create: `src/stitch/apps/operator/app.py`
- Create: `src/stitch/apps/operator/output.py`
- Create: `tests/stitch_cli/conftest.py`
- Test: `tests/stitch_cli/test_app.py`
- Test: `tests/stitch_cli/test_output.py`

- [ ] **Step 1: Write failing test for CLI scaffold**

`tests/stitch_cli/test_app.py`:
```python
from typer.testing import CliRunner

from stitch.apps.operator.app import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["system", "version"])
    assert result.exit_code == 0
    assert "stitch" in result.stdout.lower() or "0." in result.stdout
```

- [ ] **Step 2: Implement app.py**

`src/stitch/apps/operator/app.py`:
```python
"""Stitch CLI — main Typer application."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

app = typer.Typer(
    name="stitch",
    help="Stitch operator CLI — multi-client control surface.",
    no_args_is_help=True,
)

# ── Global state ──────────────────────────────────────────────

class GlobalState:
    profile: str | None = None
    output: str = "human"
    config_path: Path | None = None
    no_color: bool = False
    quiet: bool = False
    verbose: bool = False
    filters: list[str] = []
    yes: bool = False
    non_interactive: bool = False


state = GlobalState()


@app.callback()
def main_callback(
    profile: Annotated[Optional[str], typer.Option("--profile", help="Auth profile")] = None,
    output: Annotated[str, typer.Option("-o", "--output", help="Output format")] = "human",
    config: Annotated[Optional[Path], typer.Option("--config", help="Config file")] = None,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable color")] = False,
    quiet: Annotated[bool, typer.Option("--quiet", help="Minimal output")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Debug output")] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Skip confirmations")] = False,
    non_interactive: Annotated[bool, typer.Option("--non-interactive")] = False,
) -> None:
    """Global options applied to all commands."""
    state.profile = profile
    state.output = output
    state.config_path = config
    state.no_color = no_color
    state.quiet = quiet
    state.verbose = verbose
    state.yes = yes
    state.non_interactive = non_interactive

    # Auto-detect: piped output defaults to compact
    if not sys.stdout.isatty() and output == "human":
        state.output = "compact"


# ── Subcommand groups (registered in later tasks) ────────────

# Placeholder system command for scaffolding
system_app = typer.Typer(name="system", help="System health and info.")
app.add_typer(system_app)


@system_app.command("version")
def system_version() -> None:
    """Print stitch version."""
    typer.echo("stitch 0.1.0")


@system_app.command("health")
def system_health() -> None:
    """Aggregate system health."""
    typer.echo("System health check not yet connected.")


# ── Entry point ───────────────────────────────────────────────

def main() -> None:
    app()
```

- [ ] **Step 3: Run scaffold test**

Run: `uv run pytest tests/stitch_cli/test_app.py -v`
Expected: 1 passed

- [ ] **Step 4: Write failing tests for output formatters**

`tests/stitch_cli/test_output.py`:
```python
from stitch.apps.operator.output import OutputFormatter
from stitch.core.queries import QueryResult


def test_format_json():
    qr = QueryResult(
        items=[{"name": "sw-core-01", "type": "SWITCH"}],
        total=1,
    )
    fmt = OutputFormatter("json")
    out = fmt.format_result(qr)
    assert '"name": "sw-core-01"' in out
    assert '"type": "SWITCH"' in out


def test_format_compact():
    qr = QueryResult(
        items=[
            {"uri": "stitch:/device/dev_01", "name": "sw-core-01", "status": None},
            {"uri": "stitch:/device/dev_02", "name": "sw-edge-01", "status": None},
        ],
        total=2,
    )
    fmt = OutputFormatter("compact")
    out = fmt.format_result(qr)
    lines = out.strip().split("\n")
    assert len(lines) == 2
    assert "sw-core-01" in lines[0]
    assert "\t" in lines[0]


def test_format_table():
    qr = QueryResult(
        items=[
            {"name": "sw-core-01", "type": "SWITCH", "ip": "192.168.254.2"},
            {"name": "sw-edge-01", "type": "SWITCH", "ip": "192.168.254.3"},
        ],
        total=2,
    )
    fmt = OutputFormatter("table")
    out = fmt.format_result(qr)
    assert "sw-core-01" in out
    assert "sw-edge-01" in out
    # Table should have headers
    assert "name" in out.lower() or "NAME" in out


def test_format_human_single():
    qr = QueryResult(items=[{"name": "sw-core-01", "type": "SWITCH", "ip": "192.168.254.2"}], total=1)
    fmt = OutputFormatter("human")
    out = fmt.format_result(qr)
    assert "sw-core-01" in out


def test_format_yaml():
    qr = QueryResult(items=[{"name": "sw-core-01"}], total=1)
    fmt = OutputFormatter("yaml")
    out = fmt.format_result(qr)
    assert "name:" in out or "name: sw-core-01" in out
```

- [ ] **Step 5: Implement output.py**

`src/stitch/apps/operator/output.py`:
```python
"""Output formatting — human, json, table, compact, yaml."""

from __future__ import annotations

import json

import yaml
from rich.console import Console
from rich.table import Table

from stitch.core.queries import QueryResult

console = Console()


class OutputFormatter:
    def __init__(self, mode: str = "human") -> None:
        self.mode = mode

    def format_result(self, result: QueryResult) -> str:
        match self.mode:
            case "json":
                return self._format_json(result)
            case "compact":
                return self._format_compact(result)
            case "table":
                return self._format_table(result)
            case "yaml":
                return self._format_yaml(result)
            case "human":
                if result.total == 1:
                    return self._format_human_single(result.items[0])
                return self._format_table(result)
            case _:
                return self._format_json(result)

    def _format_json(self, result: QueryResult) -> str:
        if result.total == 1:
            return json.dumps(result.items[0], indent=2, default=str)
        return json.dumps(
            {"items": result.items, "total": result.total},
            indent=2,
            default=str,
        )

    def _format_compact(self, result: QueryResult) -> str:
        lines = []
        for item in result.items:
            uri = item.get("uri", item.get("id", ""))
            name = item.get("name", item.get("display_name", ""))
            status = item.get("status", "-") or "-"
            lines.append(f"{uri}\t{name}\t{status}")
        return "\n".join(lines)

    def _format_table(self, result: QueryResult) -> str:
        if not result.items:
            return "No results."
        keys = list(result.items[0].keys())
        table = Table()
        for k in keys:
            table.add_column(k.upper())
        for item in result.items:
            table.add_row(*[str(item.get(k, "")) for k in keys])

        with console.capture() as capture:
            console.print(table)
        return capture.get()

    def _format_human_single(self, item: dict) -> str:
        lines = []
        for k, v in item.items():
            if isinstance(v, list | dict):
                continue  # Skip nested for summary
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    def _format_yaml(self, result: QueryResult) -> str:
        if result.total == 1:
            return yaml.dump(result.items[0], default_flow_style=False)
        return yaml.dump(result.items, default_flow_style=False)
```

- [ ] **Step 6: Create shared CLI test fixtures**

`tests/stitch_cli/conftest.py`:
```python
"""Shared fixtures for CLI tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from stitch.core.queries import QueryResult
from stitch.sdk.client import StitchClient


@pytest.fixture
def mock_client():
    """A StitchClient with mocked query/command methods."""
    client = AsyncMock(spec=StitchClient)
    client.query = AsyncMock(return_value=QueryResult(items=[], total=0))
    client.command = AsyncMock(return_value={})
    client.close = AsyncMock()
    return client
```

- [ ] **Step 7: Run all CLI tests**

Run: `uv run pytest tests/stitch_cli/ -v`
Expected: All passed

- [ ] **Step 8: Commit**

```bash
git add src/stitch/apps/operator/ tests/stitch_cli/
git commit -m "feat(cli): scaffold with global options and output formatters"
```

---

## Task 7: CLI — Device Commands (First Golden Flow)

This task delivers `stitch device list` and `stitch device show` working end-to-end.

**Files:**
- Create: `src/stitch/apps/operator/device.py`
- Create: `src/stitch/apps/operator/_client.py`
- Modify: `src/stitch/apps/operator/app.py`
- Test: `tests/stitch_cli/test_device.py`

- [ ] **Step 1: Write failing tests for device commands**

`tests/stitch_cli/test_device.py`:
```python
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from stitch.apps.operator.app import app
from stitch.core.queries import QueryResult

runner = CliRunner()

MOCK_DEVICES = [
    {"id": "dev_01", "name": "sw-core-01", "type": "SWITCH", "model": "USW-Pro-48", "management_ip": "192.168.254.2"},
    {"id": "dev_02", "name": "fw-main", "type": "FIREWALL", "model": "OPNsense", "management_ip": "192.168.254.1"},
]


def _mock_client(query_result):
    client = AsyncMock()
    client.query = AsyncMock(return_value=query_result)
    client.command = AsyncMock(return_value={})
    client.close = AsyncMock()
    return client


@patch("stitch.apps.operator._client.get_client")
def test_device_list(mock_get_client):
    mock_get_client.return_value = _mock_client(
        QueryResult(items=MOCK_DEVICES, total=2)
    )
    result = runner.invoke(app, ["device", "list", "-o", "json"])
    assert result.exit_code == 0
    assert "sw-core-01" in result.stdout
    assert "fw-main" in result.stdout


@patch("stitch.apps.operator._client.get_client")
def test_device_show(mock_get_client):
    mock_get_client.return_value = _mock_client(
        QueryResult(items=[MOCK_DEVICES[0]], total=1)
    )
    result = runner.invoke(app, ["device", "show", "sw-core-01", "-o", "json"])
    assert result.exit_code == 0
    assert "sw-core-01" in result.stdout


@patch("stitch.apps.operator._client.get_client")
def test_device_list_with_filter(mock_get_client):
    client = _mock_client(QueryResult(items=[MOCK_DEVICES[0]], total=1))
    mock_get_client.return_value = client
    result = runner.invoke(app, ["device", "list", "--filter", "type=SWITCH", "-o", "json"])
    assert result.exit_code == 0
```

- [ ] **Step 2: Implement the client helper**

`src/stitch/apps/operator/_client.py`:
```python
"""Client lifecycle helper for CLI commands."""

from __future__ import annotations

import asyncio
import os
from functools import wraps
from typing import Any, Callable

from stitch.apps.operator.app import state
from stitch.apps.operator.output import OutputFormatter
from stitch.core.queries import QueryResult
from stitch.sdk.client import StitchClient
from stitch.sdk.config import Profile, load_config


def get_client() -> StitchClient:
    """Create a StitchClient from current global state."""
    config = load_config(state.config_path)

    # Env overrides
    env_server = os.environ.get("STITCH_SERVER")
    env_profile = os.environ.get("STITCH_PROFILE")

    profile_name = state.profile or env_profile
    if env_server:
        profile = Profile(server=env_server)
    else:
        profile = config.resolve_profile(profile_name)

    return StitchClient(profile)


def get_formatter() -> OutputFormatter:
    return OutputFormatter(state.output)


def run_async(coro):
    """Run an async function synchronously (for Typer commands)."""
    return asyncio.run(coro)
```

- [ ] **Step 3: Implement device.py**

`src/stitch/apps/operator/device.py`:
```python
"""stitch device {list,show,inspect} commands."""

from __future__ import annotations

from typing import Annotated, Optional

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async

device_app = typer.Typer(name="device", help="Device operations.")


@device_app.command("list")
def device_list(
    filter: Annotated[Optional[list[str]], typer.Option("--filter", help="Filter")] = None,
    sort: Annotated[Optional[str], typer.Option("--sort")] = None,
    limit: Annotated[Optional[int], typer.Option("--limit")] = None,
) -> None:
    """List devices."""
    async def _run():
        client = get_client()
        try:
            result = await client.query("device", "list")
            fmt = get_formatter()
            typer.echo(fmt.format_result(result))
        finally:
            await client.close()

    run_async(_run())


@device_app.command("show")
def device_show(
    device_id: Annotated[str, typer.Argument(help="Device ID or alias")],
) -> None:
    """Show device detail."""
    async def _run():
        client = get_client()
        try:
            result = await client.query("device", "show", resource_id=device_id)
            fmt = get_formatter()
            typer.echo(fmt.format_result(result))
        finally:
            await client.close()

    run_async(_run())


@device_app.command("inspect")
def device_inspect(
    device_id: Annotated[str, typer.Argument(help="Device ID or alias")],
) -> None:
    """Deep inspection: device detail + ports + neighbors."""
    async def _run():
        client = get_client()
        try:
            detail = await client.query("device", "show", resource_id=device_id)
            neighbors = await client.query("device", "neighbors", resource_id=device_id)

            fmt = get_formatter()
            typer.echo(fmt.format_result(detail))
            if neighbors.items:
                typer.echo("\nNeighbors:")
                typer.echo(fmt.format_result(neighbors))
        finally:
            await client.close()

    run_async(_run())
```

- [ ] **Step 4: Register device commands in app.py**

Add to `src/stitch/apps/operator/app.py` after the system_app registration:

```python
from stitch.apps.operator.device import device_app
app.add_typer(device_app)
```

- [ ] **Step 5: Run device tests**

Run: `uv run pytest tests/stitch_cli/test_device.py -v`
Expected: 3 passed

- [ ] **Step 6: Verify the CLI entry point works**

Run: `uv run stitch --help`
Expected: Shows help with `device`, `system` subcommands.

Run: `uv run stitch device --help`
Expected: Shows `list`, `show`, `inspect` subcommands.

- [ ] **Step 7: Commit**

```bash
git add src/stitch/apps/operator/ tests/stitch_cli/
git commit -m "feat(cli): device list, show, inspect commands"
```

---

## Task 8: CLI — Trace and Preflight Commands

**Files:**
- Create: `src/stitch/apps/operator/trace.py`
- Create: `src/stitch/apps/operator/preflight.py`
- Modify: `src/stitch/apps/operator/app.py`
- Test: `tests/stitch_cli/test_trace.py`
- Test: `tests/stitch_cli/test_preflight.py`

- [ ] **Step 1: Write failing tests for trace**

`tests/stitch_cli/test_trace.py`:
```python
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from stitch.apps.operator.app import app

runner = CliRunner()

MOCK_TRACE = {
    "vlan": 42,
    "source": "sw-core-01",
    "target": None,
    "status": "complete",
    "hops": [
        {"device": "sw-core-01", "port": "sfp-0", "status": "ok"},
        {"device": "fw-main", "port": "igb0", "status": "ok"},
    ],
}


@patch("stitch.apps.operator._client.get_client")
def test_trace_run(mock_get_client):
    client = AsyncMock()
    client.command = AsyncMock(return_value=MOCK_TRACE)
    client.close = AsyncMock()
    mock_get_client.return_value = client
    result = runner.invoke(app, ["trace", "run", "42", "--from", "sw-core-01", "-o", "json"])
    assert result.exit_code == 0
    assert "complete" in result.stdout
    client.command.assert_called_once()
```

- [ ] **Step 2: Implement trace.py**

`src/stitch/apps/operator/trace.py`:
```python
"""stitch trace {run,show,list} commands."""

from __future__ import annotations

import json
from typing import Annotated, Optional

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async

trace_app = typer.Typer(name="trace", help="VLAN path tracing.")


@trace_app.command("run")
def trace_run(
    vlan_id: Annotated[int, typer.Argument(help="VLAN ID to trace")],
    from_device: Annotated[str, typer.Option("--from", help="Source device")],
    to_device: Annotated[Optional[str], typer.Option("--to", help="Target device")] = None,
) -> None:
    """Trace a VLAN path through the topology."""
    async def _run():
        client = get_client()
        try:
            params = {"vlan": vlan_id, "source": from_device}
            if to_device:
                params["target"] = to_device
            result = await client.command("trace", "run", params=params)
            fmt = get_formatter()
            typer.echo(fmt.format_result_raw(result))
        finally:
            await client.close()

    run_async(_run())
```

- [ ] **Step 3: Add format_result_raw to OutputFormatter**

Add to `src/stitch/apps/operator/output.py`:

```python
def format_result_raw(self, data: dict) -> str:
    """Format a raw dict result (for command responses)."""
    match self.mode:
        case "json":
            return json.dumps(data, indent=2, default=str)
        case "yaml":
            return yaml.dump(data, default_flow_style=False)
        case _:
            return self._format_human_single(data)
```

- [ ] **Step 4: Write failing tests for preflight**

`tests/stitch_cli/test_preflight.py`:
```python
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from stitch.apps.operator.app import app

runner = CliRunner()

MOCK_REPORT = {
    "timestamp": "2026-04-09T12:00:00",
    "results": [],
    "summary": {"total": 16, "ok": 14, "warning": 1, "error": 1},
}


@patch("stitch.apps.operator._client.get_client")
def test_preflight_run(mock_get_client):
    client = AsyncMock()
    client.command = AsyncMock(return_value=MOCK_REPORT)
    client.close = AsyncMock()
    mock_get_client.return_value = client
    result = runner.invoke(app, ["preflight", "run", "-o", "json"])
    assert result.exit_code == 0
    assert "summary" in result.stdout
```

- [ ] **Step 5: Implement preflight.py**

`src/stitch/apps/operator/preflight.py`:
```python
"""stitch preflight run [--watch] command."""

from __future__ import annotations

from typing import Annotated

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async

preflight_app = typer.Typer(name="preflight", help="Preflight verification.")


@preflight_app.command("run")
def preflight_run(
    scope: Annotated[str | None, typer.Option("--scope", help="Scope")] = None,
    watch: Annotated[bool, typer.Option("--watch", help="Watch live")] = False,
) -> None:
    """Run preflight verification."""
    async def _run():
        client = get_client()
        try:
            params = {}
            if scope:
                params["scope"] = scope
            result = await client.command("preflight", "run", params=params or None)
            fmt = get_formatter()
            if watch:
                # TODO(task-9): implement streaming watch mode
                typer.echo(fmt.format_result_raw(result))
                typer.echo("(--watch streaming not yet implemented)", err=True)
            else:
                typer.echo(fmt.format_result_raw(result))
        finally:
            await client.close()

    run_async(_run())
```

- [ ] **Step 6: Register trace and preflight in app.py**

Add to `src/stitch/apps/operator/app.py`:

```python
from stitch.apps.operator.trace import trace_app
from stitch.apps.operator.preflight import preflight_app
app.add_typer(trace_app)
app.add_typer(preflight_app)
```

- [ ] **Step 7: Run all tests**

Run: `uv run pytest tests/stitch_cli/ -v`
Expected: All passed

- [ ] **Step 8: Commit**

```bash
git add src/stitch/apps/operator/ tests/stitch_cli/
git commit -m "feat(cli): trace run and preflight run commands"
```

---

## Task 9: SDK — WebSocket Stream Client

**Files:**
- Create: `src/stitch/sdk/streaming.py`
- Test: `tests/stitch_sdk/test_streaming.py`

- [ ] **Step 1: Write failing tests for stream client**

`tests/stitch_sdk/test_streaming.py`:
```python
import asyncio
import json

import pytest

from stitch.core.streams import StreamEvent, StreamTopic
from stitch.sdk.streaming import StreamClient


class FakeWebSocket:
    """Fake WebSocket for testing."""

    def __init__(self, messages: list[dict]):
        self._messages = [json.dumps(m) for m in messages]
        self._index = 0
        self.closed = False

    async def recv(self) -> str:
        if self._index >= len(self._messages):
            raise Exception("connection closed")
        msg = self._messages[self._index]
        self._index += 1
        return msg

    async def send(self, data: str) -> None:
        pass

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_stream_client_receives_events():
    messages = [
        {
            "event_id": "evt_001",
            "sequence": 1,
            "topic": "run.progress",
            "resource": "stitch:/run/run_18f2/task/tsk_001",
            "payload": {"status": "succeeded"},
            "timestamp": "2026-04-09T12:04:01Z",
        },
        {
            "event_id": "evt_002",
            "sequence": 2,
            "topic": "run.progress",
            "resource": "stitch:/run/run_18f2/task/tsk_002",
            "payload": {"status": "running"},
            "timestamp": "2026-04-09T12:04:03Z",
        },
    ]
    ws = FakeWebSocket(messages)
    client = StreamClient(ws)

    events = []
    async for event in client.events():
        events.append(event)
        if len(events) >= 2:
            break

    assert len(events) == 2
    assert events[0].event_id == "evt_001"
    assert events[0].topic == StreamTopic.RUN_PROGRESS
    assert events[1].payload["status"] == "running"


@pytest.mark.asyncio
async def test_stream_client_tracks_last_event_id():
    messages = [
        {"event_id": "evt_001", "sequence": 1, "topic": "run.progress",
         "resource": "r", "payload": {}, "timestamp": "2026-04-09T12:00:00Z"},
    ]
    ws = FakeWebSocket(messages)
    client = StreamClient(ws)

    async for event in client.events():
        break

    assert client.last_event_id == "evt_001"
```

- [ ] **Step 2: Implement streaming.py**

`src/stitch/sdk/streaming.py`:
```python
"""WebSocket stream client with reconnect and resume."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from stitch.core.streams import StreamEvent


class StreamClient:
    """Wraps a WebSocket connection and yields StreamEvents."""

    def __init__(self, ws) -> None:
        self._ws = ws
        self._last_event_id: str | None = None

    @property
    def last_event_id(self) -> str | None:
        return self._last_event_id

    async def events(self) -> AsyncIterator[StreamEvent]:
        """Yield StreamEvents from the WebSocket."""
        try:
            while True:
                raw = await self._ws.recv()
                data = json.loads(raw)
                event = StreamEvent(**data)
                self._last_event_id = event.event_id
                yield event
        except Exception:
            return

    async def close(self) -> None:
        await self._ws.close()
```

- [ ] **Step 3: Run stream tests**

Run: `uv run pytest tests/stitch_sdk/test_streaming.py -v`
Expected: All passed

- [ ] **Step 4: Commit**

```bash
git add src/stitch/sdk/streaming.py tests/stitch_sdk/test_streaming.py
git commit -m "feat(sdk): WebSocket stream client with event parsing"
```

---

## Task 10: CLI — Watch Mode and Run Commands

This task completes the exit criteria: `stitch preflight run --watch` and `stitch run watch <id>`.

**Files:**
- Create: `src/stitch/apps/operator/run_cmds.py`
- Create: `src/stitch/apps/operator/_watch.py`
- Modify: `src/stitch/apps/operator/preflight.py`
- Modify: `src/stitch/apps/operator/app.py`
- Modify: `src/stitch/sdk/client.py`
- Test: `tests/stitch_cli/test_run.py`

- [ ] **Step 1: Add stream_connect to StitchClient**

Add to `src/stitch/sdk/client.py`:

```python
import websockets

async def stream_connect(self, path: str = "/ws", last_event_id: str | None = None):
    """Connect to the WebSocket stream endpoint. Returns a StreamClient."""
    from stitch.sdk.streaming import StreamClient

    ws_url = self._profile.server.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url}{path}"
    headers = {}
    if last_event_id:
        headers["Last-Event-ID"] = last_event_id
    ws = await websockets.connect(ws_url, additional_headers=headers)
    return StreamClient(ws)
```

- [ ] **Step 2: Create the watch display helper**

`src/stitch/apps/operator/_watch.py`:
```python
"""Watch mode — live display for run progress and logs."""

from __future__ import annotations

import sys

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

from stitch.core.streams import StreamEvent

console = Console(stderr=True)

_STATUS_STYLES = {
    "succeeded": "green",
    "running": "yellow",
    "failed": "red",
    "cancelled": "dim",
    "timed_out": "red",
    "pending": "dim",
    "queued": "dim",
}


def render_watch_event(event: StreamEvent) -> None:
    """Print a single stream event to stderr in watch mode."""
    status = event.payload.get("status", "")
    style = _STATUS_STYLES.get(status, "")
    description = event.payload.get("description", event.resource)
    task_id = event.payload.get("task_id", "")

    prefix = f"  {task_id}" if task_id else ""
    status_text = Text(status.upper(), style=style) if style else Text(status.upper())

    console.print(f"{prefix} {status_text} {description}", highlight=False)


def render_watch_complete(result: dict) -> None:
    """Print final watch summary to stderr."""
    status = result.get("status", "unknown")
    style = _STATUS_STYLES.get(status, "")
    console.print(f"\nRun {result.get('run_id', '?')}: {Text(status.upper(), style=style)}")
```

- [ ] **Step 3: Write failing tests for run commands**

`tests/stitch_cli/test_run.py`:
```python
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from stitch.apps.operator.app import app
from stitch.core.queries import QueryResult

runner = CliRunner()

MOCK_RUNS = [
    {"run_id": "run_4f8a", "status": "running", "description": "preflight site-rdam"},
    {"run_id": "run_3e1b", "status": "succeeded", "description": "preflight site-ams"},
]


@patch("stitch.apps.operator._client.get_client")
def test_run_list(mock_get_client):
    client = AsyncMock()
    client.query = AsyncMock(return_value=QueryResult(items=MOCK_RUNS, total=2))
    client.close = AsyncMock()
    mock_get_client.return_value = client
    result = runner.invoke(app, ["run", "list", "-o", "json"])
    assert result.exit_code == 0
    assert "run_4f8a" in result.stdout


@patch("stitch.apps.operator._client.get_client")
def test_run_show(mock_get_client):
    client = AsyncMock()
    client.query = AsyncMock(return_value=QueryResult(items=[MOCK_RUNS[0]], total=1))
    client.close = AsyncMock()
    mock_get_client.return_value = client
    result = runner.invoke(app, ["run", "show", "run_4f8a", "-o", "json"])
    assert result.exit_code == 0
    assert "running" in result.stdout
```

- [ ] **Step 4: Implement run_cmds.py**

`src/stitch/apps/operator/run_cmds.py`:
```python
"""stitch run {create,show,list,watch,execute,cancel} commands."""

from __future__ import annotations

from typing import Annotated, Optional

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async

run_app = typer.Typer(name="run", help="Run orchestration lifecycle.")


@run_app.command("list")
def run_list(
    filter: Annotated[Optional[list[str]], typer.Option("--filter")] = None,
) -> None:
    """List runs."""
    async def _run():
        client = get_client()
        try:
            result = await client.query("run", "list")
            fmt = get_formatter()
            typer.echo(fmt.format_result(result))
        finally:
            await client.close()

    run_async(_run())


@run_app.command("show")
def run_show(
    run_id: Annotated[str, typer.Argument(help="Run ID")],
) -> None:
    """Show run detail."""
    async def _run():
        client = get_client()
        try:
            result = await client.query("run", "show", resource_id=run_id)
            fmt = get_formatter()
            typer.echo(fmt.format_result(result))
        finally:
            await client.close()

    run_async(_run())


@run_app.command("watch")
def run_watch(
    run_id: Annotated[str, typer.Argument(help="Run ID to watch")],
) -> None:
    """Watch a run's progress live."""
    from stitch.apps.operator._watch import render_watch_complete, render_watch_event

    async def _run():
        client = get_client()
        try:
            # First fetch current state
            result = await client.query("run", "show", resource_id=run_id)
            if result.items:
                run_data = result.items[0]
                status = run_data.get("status", "")
                if status in ("succeeded", "failed", "cancelled", "timed_out"):
                    fmt = get_formatter()
                    typer.echo(fmt.format_result(result))
                    return

            # Connect to stream
            typer.echo(f"Watching run {run_id}...", err=True)
            try:
                stream = await client.stream_connect(f"/ws/runs/{run_id}")
                async for event in stream.events():
                    render_watch_event(event)
                    # Check for terminal state
                    status = event.payload.get("status", "")
                    if status in ("succeeded", "failed", "cancelled", "timed_out"):
                        render_watch_complete(event.payload)
                        break
            except Exception as e:
                typer.echo(f"Stream error: {e}", err=True)
                typer.echo("Falling back to poll mode.", err=True)
                # Fallback: just show current state
                result = await client.query("run", "show", resource_id=run_id)
                fmt = get_formatter()
                typer.echo(fmt.format_result(result))
        finally:
            await client.close()

    run_async(_run())


@run_app.command("execute")
def run_execute(
    run_id: Annotated[str, typer.Argument(help="Run ID")],
) -> None:
    """Execute a planned run."""
    async def _run():
        client = get_client()
        try:
            result = await client.command("run", "execute", resource_id=run_id)
            fmt = get_formatter()
            typer.echo(fmt.format_result_raw(result))
        finally:
            await client.close()

    run_async(_run())


@run_app.command("cancel")
def run_cancel(
    run_id: Annotated[str, typer.Argument(help="Run ID")],
    reason: Annotated[Optional[str], typer.Option("--reason")] = None,
) -> None:
    """Cancel an in-progress run."""
    async def _run():
        client = get_client()
        try:
            params = {"reason": reason} if reason else None
            result = await client.command("run", "cancel", resource_id=run_id, params=params)
            fmt = get_formatter()
            typer.echo(fmt.format_result_raw(result))
        finally:
            await client.close()

    run_async(_run())
```

- [ ] **Step 5: Update preflight.py to use watch mode**

Replace the watch placeholder in `src/stitch/apps/operator/preflight.py`:

```python
@preflight_app.command("run")
def preflight_run(
    scope: Annotated[str | None, typer.Option("--scope", help="Scope")] = None,
    watch: Annotated[bool, typer.Option("--watch", help="Watch live")] = False,
) -> None:
    """Run preflight verification."""
    from stitch.apps.operator._watch import render_watch_complete, render_watch_event

    async def _run():
        client = get_client()
        try:
            params = {}
            if scope:
                params["scope"] = scope
            result = await client.command("preflight", "run", params=params or None)

            if watch and "run_id" in result:
                run_id = result["run_id"]
                typer.echo(f"Run started: {run_id} (preflight)", err=True)
                try:
                    stream = await client.stream_connect(f"/ws/runs/{run_id}")
                    async for event in stream.events():
                        render_watch_event(event)
                        status = event.payload.get("status", "")
                        if status in ("succeeded", "failed", "cancelled", "timed_out"):
                            render_watch_complete(event.payload)
                            break
                except Exception:
                    typer.echo("Stream unavailable, showing result.", err=True)
                    fmt = get_formatter()
                    typer.echo(fmt.format_result_raw(result))
            else:
                fmt = get_formatter()
                typer.echo(fmt.format_result_raw(result))
                if "run_id" in result:
                    typer.echo(
                        f"Use `stitch run watch {result['run_id']}` to follow progress.",
                        err=True,
                    )
        finally:
            await client.close()

    run_async(_run())
```

- [ ] **Step 6: Register run commands in app.py**

Add to `src/stitch/apps/operator/app.py`:

```python
from stitch.apps.operator.run_cmds import run_app
app.add_typer(run_app)
```

- [ ] **Step 7: Run all tests**

Run: `uv run pytest tests/stitch_cli/ tests/stitch_sdk/ tests/stitch_core/ -v`
Expected: All passed

- [ ] **Step 8: Commit**

```bash
git add src/stitch/ tests/
git commit -m "feat(cli): run commands with watch mode and stream client"
```

---

## Task 11: Remaining CLI Commands

Implements the remaining resource commands to round out the CLI vocabulary. Each follows the same pattern established in Tasks 7-8.

**Files:**
- Create: `src/stitch/apps/operator/topology.py`
- Create: `src/stitch/apps/operator/review.py`
- Create: `src/stitch/apps/operator/report.py`
- Create: `src/stitch/apps/operator/impact.py`
- Create: `src/stitch/apps/operator/search.py`
- Create: `src/stitch/apps/operator/show.py`
- Modify: `src/stitch/apps/operator/app.py`

- [ ] **Step 1: Implement topology.py**

`src/stitch/apps/operator/topology.py`:
```python
"""stitch topology {show,export,diff,diagnostics} commands."""

from __future__ import annotations

from typing import Annotated, Optional

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async

topology_app = typer.Typer(name="topology", help="Topology operations.")


@topology_app.command("show")
def topology_show() -> None:
    """Show topology summary."""
    async def _run():
        client = get_client()
        try:
            result = await client.query("topology", "show")
            typer.echo(get_formatter().format_result(result))
        finally:
            await client.close()
    run_async(_run())


@topology_app.command("diagnostics")
def topology_diagnostics() -> None:
    """Show topology diagnostics (dangling ports, orphans, etc.)."""
    async def _run():
        client = get_client()
        try:
            result = await client.query("topology", "diagnostics")
            typer.echo(get_formatter().format_result(result))
        finally:
            await client.close()
    run_async(_run())


@topology_app.command("export")
def topology_export(
    format: Annotated[str, typer.Option("--format")] = "json",
) -> None:
    """Export full topology snapshot."""
    async def _run():
        from stitch.apps.operator.output import OutputFormatter
        client = get_client()
        try:
            result = await client.query("topology", "show")
            fmt = OutputFormatter(format)
            typer.echo(fmt.format_result(result))
        finally:
            await client.close()
    run_async(_run())


@topology_app.command("diff")
def topology_diff(
    before: Annotated[str, typer.Argument(help="Before snapshot/report ID or file")],
    after: Annotated[str, typer.Argument(help="After snapshot/report ID or file")],
) -> None:
    """Compare two topology snapshots or reports."""
    async def _run():
        client = get_client()
        try:
            result = await client.command(
                "topology", "diff", params={"before": before, "after": after}
            )
            typer.echo(get_formatter().format_result_raw(result))
        finally:
            await client.close()
    run_async(_run())
```

- [ ] **Step 2: Implement review.py**

`src/stitch/apps/operator/review.py`:
```python
"""stitch review {request,show,list,approve,reject} commands."""

from __future__ import annotations

from typing import Annotated, Optional

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async

review_app = typer.Typer(name="review", help="Review and approval workflow.")


@review_app.command("show")
def review_show(review_id: Annotated[str, typer.Argument()]) -> None:
    """Show review detail and findings."""
    async def _run():
        client = get_client()
        try:
            result = await client.query("run", "show", resource_id=review_id)
            typer.echo(get_formatter().format_result(result))
        finally:
            await client.close()
    run_async(_run())


@review_app.command("list")
def review_list(
    filter: Annotated[Optional[list[str]], typer.Option("--filter")] = None,
) -> None:
    """List reviews."""
    async def _run():
        client = get_client()
        try:
            result = await client.query("run", "list")
            typer.echo(get_formatter().format_result(result))
        finally:
            await client.close()
    run_async(_run())


@review_app.command("request")
def review_request(run_id: Annotated[str, typer.Argument()]) -> None:
    """Request a review for a run."""
    async def _run():
        client = get_client()
        try:
            result = await client.command("run", "review", resource_id=run_id)
            typer.echo(get_formatter().format_result_raw(result))
        finally:
            await client.close()
    run_async(_run())


@review_app.command("approve")
def review_approve(
    review_id: Annotated[str, typer.Argument()],
    comment: Annotated[Optional[str], typer.Option("--comment")] = None,
) -> None:
    """Approve a review."""
    from stitch.apps.operator.app import state
    if not state.yes:
        typer.confirm("Approve this review?", abort=True)
    async def _run():
        client = get_client()
        try:
            params = {"comment": comment} if comment else None
            result = await client.command("run", "review", resource_id=review_id, params=params)
            typer.echo(get_formatter().format_result_raw(result))
        finally:
            await client.close()
    run_async(_run())


@review_app.command("reject")
def review_reject(
    review_id: Annotated[str, typer.Argument()],
    comment: Annotated[Optional[str], typer.Option("--comment")] = None,
) -> None:
    """Reject a review."""
    from stitch.apps.operator.app import state
    if not state.yes:
        typer.confirm("Reject this review?", abort=True)
    async def _run():
        client = get_client()
        try:
            params = {"action": "reject", "comment": comment}
            result = await client.command("run", "review", resource_id=review_id, params=params)
            typer.echo(get_formatter().format_result_raw(result))
        finally:
            await client.close()
    run_async(_run())
```

- [ ] **Step 3: Implement remaining commands (impact, report, search, show)**

`src/stitch/apps/operator/impact.py`:
```python
"""stitch impact {preview,show,list} commands."""

from __future__ import annotations

from typing import Annotated, Optional

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async

impact_app = typer.Typer(name="impact", help="Change impact analysis.")


@impact_app.command("preview")
def impact_preview(
    action: Annotated[str, typer.Option("--action", help="Action type")],
    device: Annotated[str, typer.Option("--device", help="Target device")],
    port: Annotated[str, typer.Option("--port", help="Target port")],
) -> None:
    """Preview impact of a proposed change."""
    async def _run():
        client = get_client()
        try:
            result = await client.command(
                "impact", "preview",
                params={"action": action, "device": device, "port": port},
            )
            typer.echo(get_formatter().format_result_raw(result))
        finally:
            await client.close()
    run_async(_run())
```

`src/stitch/apps/operator/report.py`:
```python
"""stitch report {show,list,diff} commands."""

from __future__ import annotations

from typing import Annotated, Optional

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async

report_app = typer.Typer(name="report", help="Verification reports.")


@report_app.command("show")
def report_show(report_id: Annotated[str, typer.Argument(help="Report ID or 'latest'")]) -> None:
    """Show a verification report."""
    async def _run():
        client = get_client()
        try:
            result = await client.query("topology", "show")  # maps to current report
            typer.echo(get_formatter().format_result(result))
        finally:
            await client.close()
    run_async(_run())


@report_app.command("diff")
def report_diff(
    id1: Annotated[str, typer.Argument(help="First report ID")],
    id2: Annotated[str, typer.Argument(help="Second report ID")],
) -> None:
    """Compare two reports."""
    async def _run():
        client = get_client()
        try:
            result = await client.command(
                "topology", "diff", params={"before": id1, "after": id2}
            )
            typer.echo(get_formatter().format_result_raw(result))
        finally:
            await client.close()
    run_async(_run())
```

`src/stitch/apps/operator/search.py`:
```python
"""stitch search command."""

from __future__ import annotations

from typing import Annotated, Optional

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async
from stitch.core.queries import QueryResult


def search_command(
    text: Annotated[str, typer.Argument(help="Search text")],
    type: Annotated[Optional[str], typer.Option("--type")] = None,
    limit: Annotated[int, typer.Option("--limit")] = 20,
) -> None:
    """Search across all resources."""
    async def _run():
        client = get_client()
        try:
            # Search across device names as a basic v1
            result = await client.query("device", "list")
            filtered = [
                item for item in result.items
                if text.lower() in str(item).lower()
            ]
            typer.echo(get_formatter().format_result(
                QueryResult(items=filtered[:limit], total=len(filtered))
            ))
        finally:
            await client.close()
    run_async(_run())
```

`src/stitch/apps/operator/show.py`:
```python
"""stitch show <uri> — open any resource by stitch URI."""

from __future__ import annotations

from typing import Annotated

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async
from stitch.core.resources import parse_uri


def show_command(
    uri: Annotated[str, typer.Argument(help="Stitch URI (stitch:/device/dev_01HX)")],
) -> None:
    """Open any resource by its stitch URI."""
    async def _run():
        parsed = parse_uri(uri)
        client = get_client()
        try:
            result = await client.query(
                parsed.resource_type, "show", resource_id=parsed.resource_id
            )
            typer.echo(get_formatter().format_result(result))
        finally:
            await client.close()
    run_async(_run())
```

- [ ] **Step 4: Register all commands in app.py**

Update `src/stitch/apps/operator/app.py` to add all subcommand registrations:

```python
# ── Register all subcommand groups ────────────────────────────
from stitch.apps.operator.device import device_app
from stitch.apps.operator.impact import impact_app
from stitch.apps.operator.preflight import preflight_app
from stitch.apps.operator.report import report_app
from stitch.apps.operator.review import review_app
from stitch.apps.operator.run_cmds import run_app
from stitch.apps.operator.search import search_command
from stitch.apps.operator.show import show_command
from stitch.apps.operator.topology import topology_app
from stitch.apps.operator.trace import trace_app

app.add_typer(device_app)
app.add_typer(impact_app)
app.add_typer(preflight_app)
app.add_typer(report_app)
app.add_typer(review_app)
app.add_typer(run_app)
app.add_typer(topology_app)
app.add_typer(trace_app)
app.command("search")(search_command)
app.command("show")(show_command)
```

- [ ] **Step 5: Verify full CLI help**

Run: `uv run stitch --help`
Expected: Shows all subcommands: device, impact, preflight, report, review, run, search, show, system, topology, trace.

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest tests/stitch_core/ tests/stitch_sdk/ tests/stitch_cli/ -v`
Expected: All passed

- [ ] **Step 7: Run lint**

Run: `uv run ruff check src/stitch/ tests/stitch_core/ tests/stitch_sdk/ tests/stitch_cli/`
Expected: No errors (fix any that appear)

- [ ] **Step 8: Commit**

```bash
git add src/stitch/ tests/
git commit -m "feat(cli): complete command vocabulary — topology, review, report, impact, search, show"
```

---

## Task 12: Integration Smoke Test Against Live Lab

This is the exit criteria validation. Run the four required commands against the actual lab.

**Prerequisite:** The stitch-workbench API must be running on the lab. Configure `~/.config/stitch/config.yaml` with the lab server URL.

- [ ] **Step 1: Create config file**

```yaml
# ~/.config/stitch/config.yaml
default_profile: lab
profiles:
  lab:
    server: http://localhost:8000
```

- [ ] **Step 2: Test `stitch device list`**

Run: `uv run stitch device list`
Expected: Shows lab devices (sw-core-01, fw-main, proxmox-01, etc.) in human-readable format.

Run: `uv run stitch device list -o json`
Expected: JSON array of device objects.

Run: `uv run stitch device list -o compact`
Expected: TAB-separated lines, one per device.

- [ ] **Step 3: Test `stitch device show`**

Run: `uv run stitch device show sw-core-01`
Expected: Device detail with name, type, model, IP, ports.

- [ ] **Step 4: Test `stitch trace run`**

Run: `uv run stitch trace run 42 --from sw-core-01 -o json`
Expected: Trace result with hops and status.

- [ ] **Step 5: Test `stitch preflight run`**

Run: `uv run stitch preflight run -o json`
Expected: Verification report with results and summary.

- [ ] **Step 6: Test `stitch topology diagnostics`**

Run: `uv run stitch topology diagnostics -o json`
Expected: Diagnostics with dangling ports, orphan devices, etc.

- [ ] **Step 7: Test `stitch system health`**

Run: `uv run stitch system health`
Expected: System health status.

- [ ] **Step 8: Document any endpoint adjustments needed**

If any commands fail due to endpoint mismatch, update `src/stitch/sdk/endpoints.py` to match the actual API paths. Fix and re-test.

- [ ] **Step 9: Commit any fixes**

```bash
git add src/stitch/
git commit -m "fix(sdk): align endpoint mapping with live lab API"
```

- [ ] **Step 10: Final exit criteria check**

Verify all four spec exit criteria:
1. `stitch device list` — works
2. `stitch preflight run --watch` — works (or gracefully falls back if no WebSocket endpoint yet)
3. `stitch trace run 42 --from sw-core-01` — works
4. `stitch run watch <id>` — works (or gracefully falls back)

If streaming endpoints don't exist yet on the backend, the CLI should fall back to polling/single-result mode. That's acceptable for Phase 1 — the stream client is ready for when the backend adds WebSocket support.

---

## Self-Review Checklist

**Spec coverage:**
- [x] §3.1 Resource identity — Task 2 (ResourceURI, parse_uri)
- [x] §3.2 Command model — Task 3 (Command, CommandSpec, CommandSource)
- [x] §3.3 Query model — Task 3 (Query, Filter, FilterOp, QueryResult, parse_filter)
- [x] §3.4 Stream model — Task 3 (StreamSubscription, StreamTopic, StreamEvent)
- [x] §3.5 Auth — Task 4 (config, profiles, token resolution)
- [x] §3.7 Errors — Task 2 (StitchError, TransportError)
- [x] §3.8 Lifecycle — Task 2 (LifecycleState, transitions)
- [x] §5 Command vocabulary — Task 7-11 (all CLI commands)
- [x] §6.1 Typer entry point — Task 1, 6
- [x] §6.2 Command tree — Tasks 7-11
- [x] §6.3 Output modes — Task 6 (human, json, table, compact, yaml)
- [x] §6.4 Streaming — Task 9-10 (StreamClient, watch mode)
- [x] §6.5 Batch input — deferred (not in exit criteria, can add post-Phase 1)
- [x] §6.6 Exit codes — partially covered (Typer handles most, custom codes deferred)
- [x] §6.7 Config — Task 4

**Not covered (acceptable for Phase 1):**
- §6.5 Batch input (--from-stdin, --targets-file) — no exit criteria depend on this
- §6.8 Shell completion — Typer provides basics, custom completion can follow
- §3.6 Capability discovery — backend doesn't serve this yet
- WebSocket endpoint on the backend — the client is ready, backend may need Phase 1 backend work

**Type consistency:** All types used in later tasks (StitchClient, QueryResult, OutputFormatter, StreamClient) match their definitions in earlier tasks. Verified.
