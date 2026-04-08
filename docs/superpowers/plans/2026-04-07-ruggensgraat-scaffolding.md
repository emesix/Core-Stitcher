# VOS-Ruggensgraat Scaffolding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate VOS-Workbench code, create spine SDK, contractkit, modelkit, and all module stubs so the repo is ready for domain development.

**Architecture:** Monorepo with `vos_workbench` (unchanged spine) alongside `vos.*` namespace packages. Pure libraries have no spine dependency. Runtime modules register via entry points and import only `vos_workbench.sdk.*`.

**Tech Stack:** Python 3.14, Pydantic v2, FastAPI, SQLModel, structlog, ruff, pytest, uv

**Spec:** `docs/superpowers/specs/2026-04-07-ruggensgraat-architecture-design.md`

---

## File Map

### Migrated (from VOS-Workbench-standalone)

| Source | Destination |
|--------|-------------|
| `Merger targets/VOS-Workbench-standalone/src/vos_workbench/` | `src/vos_workbench/` |
| `Merger targets/VOS-Workbench-standalone/tests/*.py` | `tests/vos_workbench/` |
| `Merger targets/VOS-Workbench-standalone/alembic/` | `alembic/` |
| `Merger targets/VOS-Workbench-standalone/schemas/` | `schemas/` |
| `Merger targets/VOS-Workbench-standalone/alembic.ini` | `alembic.ini` |
| `Merger targets/VOS-Workbench-standalone/.python-version` | `.python-version` |
| `Merger targets/VOS-Workbench-standalone/docs/architecture/` | `docs/architecture/` |
| `Merger targets/VOS-Network-Redux/docs/superpowers/specs/*preflight*` | `docs/specs/` |
| `Merger targets/VOS-Network-Redux/docs/superpowers/specs/*network-topology*` | `docs/specs/` |

### New — Spine SDK

| File | Responsibility |
|------|---------------|
| `src/vos_workbench/sdk/__init__.py` | Re-export public SDK surface |
| `src/vos_workbench/sdk/module_type.py` | `ModuleType` protocol with lifecycle hooks |
| `src/vos_workbench/sdk/manifest.py` | `ModuleManifest` dataclass |
| `src/vos_workbench/sdk/events.py` | `EventPublisher`, `EventSubscription` protocols |
| `src/vos_workbench/sdk/config.py` | `ConfigAccessor` protocol |
| `src/vos_workbench/sdk/context.py` | `ModuleContext` container |
| `src/vos_workbench/sdk/capabilities.py` | `CapabilityResolver` protocol |
| `tests/vos_workbench/test_sdk.py` | SDK protocol conformance tests |

### New — contractkit

| File | Responsibility |
|------|---------------|
| `src/vos/contractkit/__init__.py` | Re-export all protocols |
| `src/vos/contractkit/collector.py` | `CollectorProtocol` |
| `src/vos/contractkit/merger.py` | `MergerProtocol` |
| `src/vos/contractkit/verifier.py` | `VerifierProtocol` |
| `src/vos/contractkit/tracer.py` | `TracerProtocol` |
| `src/vos/contractkit/workflow.py` | `PreflightWorkflowProtocol` |
| `src/vos/contractkit/health.py` | `ModuleHealth`, `ModuleStatus` |
| `tests/contractkit/test_protocols.py` | Protocol structural tests |

### New — modelkit

| File | Responsibility |
|------|---------------|
| `src/vos/modelkit/__init__.py` | Re-export all domain types |
| `src/vos/modelkit/enums.py` | `DeviceType`, `PortType`, `LinkType`, `ObservationSource`, `VlanMode` |
| `src/vos/modelkit/device.py` | `Device`, `Position` |
| `src/vos/modelkit/port.py` | `Port`, `VlanMembership`, `ExpectedNeighbor` |
| `src/vos/modelkit/link.py` | `Link`, `LinkEndpoint` |
| `src/vos/modelkit/vlan.py` | `VlanMetadata` |
| `src/vos/modelkit/topology.py` | `TopologySnapshot`, `TopologyMeta` |
| `src/vos/modelkit/observation.py` | `Observation`, `Mismatch`, `MergeConflict` |
| `src/vos/modelkit/verification.py` | `CheckResult`, `LinkVerification`, `VerificationReport` |
| `src/vos/modelkit/trace.py` | `TraceRequest`, `TraceHop`, `TraceResult`, `BreakPoint` |
| `src/vos/modelkit/impact.py` | `ImpactRequest`, `ImpactEffect`, `ImpactResult` |
| `tests/modelkit/test_enums.py` | Enum coverage |
| `tests/modelkit/test_device.py` | Device construction + validation |
| `tests/modelkit/test_port.py` | Port + VlanMembership validation |
| `tests/modelkit/test_link.py` | Link construction + endpoint validation |
| `tests/modelkit/test_topology.py` | TopologySnapshot construction |
| `tests/modelkit/test_observation.py` | Observation + Mismatch construction |
| `tests/modelkit/test_verification.py` | VerificationReport construction |
| `tests/modelkit/test_trace.py` | TraceRequest/Result construction |
| `tests/modelkit/test_impact.py` | ImpactRequest/Result construction |

### New — Module Stubs

| File | Responsibility |
|------|---------------|
| `src/vos/graphkit/__init__.py` | Stub with docstring |
| `src/vos/storekit/__init__.py` | Stub with docstring |
| `src/vos/switchcraft/__init__.py` | Module class skeleton |
| `src/vos/opnsensecraft/__init__.py` | Module class skeleton |
| `src/vos/proxmoxcraft/__init__.py` | Module class skeleton |
| `src/vos/collectkit/__init__.py` | Module class skeleton |
| `src/vos/verifykit/__init__.py` | Module class skeleton |
| `src/vos/tracekit/__init__.py` | Module class skeleton |
| `src/vos/interfacekit/__init__.py` | Module class skeleton |
| `src/vos/apps/__init__.py` | Namespace marker |
| `src/vos/apps/preflight/__init__.py` | App shell stub |

---

## Task 1: Migrate VOS-Workbench into VOS-Ruggensgraat

**Files:**
- Create: `src/vos_workbench/` (copied from Merger targets)
- Create: `tests/vos_workbench/` (copied from Merger targets)
- Create: `alembic/`, `schemas/`, `alembic.ini`, `.python-version`
- Create: `docs/architecture/`, `docs/specs/`
- Create: `pyproject.toml` (copied and adapted)
- Create: `.gitignore`

- [ ] **Step 1: Copy source code and infrastructure**

```bash
# Spine source
cp -r "Merger targets/VOS-Workbench-standalone/src/vos_workbench" src/vos_workbench

# Tests — move to subdirectory for namespace separation
mkdir -p tests/vos_workbench
cp "Merger targets/VOS-Workbench-standalone/tests/"*.py tests/vos_workbench/

# Infrastructure
cp -r "Merger targets/VOS-Workbench-standalone/alembic" alembic
cp -r "Merger targets/VOS-Workbench-standalone/schemas" schemas
cp "Merger targets/VOS-Workbench-standalone/alembic.ini" alembic.ini
cp "Merger targets/VOS-Workbench-standalone/.python-version" .python-version
cp "Merger targets/VOS-Workbench-standalone/.gitignore" .gitignore
cp "Merger targets/VOS-Workbench-standalone/pyrightconfig.json" pyrightconfig.json
```

- [ ] **Step 2: Copy architecture docs and design specs**

```bash
# Architecture docs from Workbench
cp -r "Merger targets/VOS-Workbench-standalone/docs/architecture" docs/architecture

# Design specs from Network-Redux
mkdir -p docs/specs
cp "Merger targets/VOS-Network-Redux/docs/superpowers/specs/2026-04-07-vos-preflight-final-design.md" docs/specs/
cp "Merger targets/VOS-Network-Redux/docs/superpowers/specs/2026-04-07-network-topology-visualizer-design.md" docs/specs/
cp "Merger targets/VOS-Network-Redux/docs/superpowers/specs/2026-04-07-vos-preflight-counter-proposal.md" docs/specs/
cp "Merger targets/VOS-Network-Redux/docs/superpowers/specs/CHATGPT-COncept finalization.md" docs/specs/
```

- [ ] **Step 3: Create pyproject.toml**

```toml
[project]
name = "vos-ruggensgraat"
version = "0.1.0"
description = "Modular agentic backend with network topology verification"
readme = "README.md"
authors = [
    { name = "emesix", email = "emesix@xs4all.nl" }
]
requires-python = ">=3.14"
dependencies = [
    "alembic>=1.18.4",
    "fastapi>=0.135.3",
    "httpx>=0.28.1",
    "pydantic>=2.12.5",
    "pydantic-settings>=2.13.1",
    "pyyaml>=6.0.3",
    "sqlmodel>=0.0.38",
    "structlog>=25.5.0",
    "uvicorn[standard]>=0.42.0",
    "websockets>=16.0",
]

[project.scripts]
vos-workbench = "vos_workbench:main"

# Module type entry points — register built-in module types here.
[project.entry-points."vos.modules"]

[build-system]
requires = ["uv_build>=0.11.1,<0.12.0"]
build-backend = "uv_build"

[dependency-groups]
dev = [
    "pyright>=1.1.408",
    "pytest>=9.0.2",
    "pytest-asyncio>=1.3.0",
    "pytest-cov>=7.1.0",
    "ruff>=0.15.9",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py314"
line-length = 100

[tool.ruff.lint]
select = [
    "E",     # pycodestyle errors
    "W",     # pycodestyle warnings
    "F",     # pyflakes
    "I",     # isort
    "UP",    # pyupgrade
    "B",     # flake8-bugbear
    "SIM",   # flake8-simplify
    "TCH",   # type-checking imports
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["TCH003"]

[tool.ruff.lint.isort]
known-first-party = ["vos_workbench", "vos"]
```

- [ ] **Step 4: Add `__init__.py` to tests/vos_workbench**

Create empty `tests/vos_workbench/__init__.py` so pytest discovers the subdirectory.

- [ ] **Step 5: Create and activate venv, install**

```bash
uv venv
uv pip install -e ".[dev]"
```

- [ ] **Step 6: Run existing tests to verify migration**

```bash
uv run pytest tests/vos_workbench/ -v
```

Expected: All 20+ existing tests pass. If any fail due to path changes (e.g., Alembic directory resolution), fix the relative path in `src/vos_workbench/storage/database.py` — the `_ALEMBIC_DIR` uses `parents[3]` which should still resolve to repo root.

- [ ] **Step 7: Run lint**

```bash
uv run ruff check src/ tests/
```

Expected: Clean.

- [ ] **Step 8: Commit**

```bash
git add src/ tests/ alembic/ schemas/ docs/architecture/ docs/specs/ \
    pyproject.toml alembic.ini .python-version .gitignore pyrightconfig.json
git commit -m "feat: migrate VOS-Workbench and design specs into VOS-Ruggensgraat

Copy vos_workbench source, tests, alembic, schemas unchanged.
Copy preflight/netmap design specs from VOS-Network-Redux.
Single pyproject.toml as vos-ruggensgraat."
```

---

## Task 2: Create Spine SDK — Protocol Definitions

**Files:**
- Create: `src/vos_workbench/sdk/__init__.py`
- Create: `src/vos_workbench/sdk/module_type.py`
- Create: `src/vos_workbench/sdk/manifest.py`
- Create: `src/vos_workbench/sdk/events.py`
- Create: `src/vos_workbench/sdk/config.py`
- Create: `src/vos_workbench/sdk/context.py`
- Create: `src/vos_workbench/sdk/capabilities.py`
- Test: `tests/vos_workbench/test_sdk.py`

- [ ] **Step 1: Write failing tests for SDK protocols**

```python
# tests/vos_workbench/test_sdk.py
from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest

from vos_workbench.sdk import (
    CapabilityResolver,
    ConfigAccessor,
    EventPublisher,
    ModuleContext,
    ModuleManifest,
    ModuleType,
)


class FakeConfig:
    host: str = "10.0.0.1"


class FakePublisher:
    def __init__(self) -> None:
        self.events: list[Any] = []

    async def publish(self, event: Any) -> None:
        self.events.append(event)


class FakeConfigAccessor:
    def __init__(self, config: Any) -> None:
        self._config = config

    def get(self) -> Any:
        return self._config


class FakeResolver:
    def resolve_one[T](self, protocol: type[T], *, selector: str | None = None) -> T:
        raise NotImplementedError

    def resolve_all[T](self, protocol: type[T]) -> list[T]:
        return []

    def resolve_named[T](self, protocol: type[T], instance_id: str | UUID) -> T:
        raise NotImplementedError


class FakeModule:
    type_name = "resource.fake"
    version = "0.1.0"
    config_model = FakeConfig
    manifest = ModuleManifest(
        capabilities_provided=["collect"],
        capabilities_required=[],
    )

    async def start(self, context: ModuleContext) -> None:
        self._context = context

    async def stop(self) -> None:
        pass

    async def health(self) -> dict:
        return {"status": "ok"}


def test_module_type_protocol_conformance():
    """FakeModule satisfies ModuleType protocol."""
    mod = FakeModule()
    assert isinstance(mod, ModuleType)
    assert mod.type_name == "resource.fake"
    assert mod.version == "0.1.0"
    assert mod.config_model is FakeConfig


def test_module_manifest_fields():
    manifest = ModuleManifest(
        capabilities_provided=["collect", "observe"],
        capabilities_required=["eventbus"],
    )
    assert manifest.capabilities_provided == ["collect", "observe"]
    assert manifest.capabilities_required == ["eventbus"]


def test_module_context_bundles_services():
    publisher = FakePublisher()
    config_accessor = FakeConfigAccessor(FakeConfig())
    resolver = FakeResolver()

    ctx = ModuleContext(
        module_name="fake-1",
        module_uuid="00000000-0000-0000-0000-000000000001",
        publisher=publisher,
        config=config_accessor,
        capabilities=resolver,
    )

    assert ctx.module_name == "fake-1"
    assert ctx.publisher is publisher
    assert ctx.config is config_accessor
    assert ctx.capabilities is resolver


def test_event_publisher_protocol():
    pub = FakePublisher()
    assert isinstance(pub, EventPublisher)


def test_config_accessor_protocol():
    acc = FakeConfigAccessor(FakeConfig())
    assert isinstance(acc, ConfigAccessor)


def test_capability_resolver_protocol():
    res = FakeResolver()
    assert isinstance(res, CapabilityResolver)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/vos_workbench/test_sdk.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'vos_workbench.sdk'`

- [ ] **Step 3: Implement `vos_workbench/sdk/manifest.py`**

```python
# src/vos_workbench/sdk/manifest.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModuleManifest:
    """Declares what a module type provides and requires.

    Belongs to the ModuleType (class-level), not to instances.
    """

    capabilities_provided: list[str] = field(default_factory=list)
    capabilities_required: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Implement `vos_workbench/sdk/events.py`**

```python
# src/vos_workbench/sdk/events.py
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EventPublisher(Protocol):
    """Publish events for audit/telemetry. Injected via ModuleContext."""

    async def publish(self, event: Any) -> None: ...
```

- [ ] **Step 5: Implement `vos_workbench/sdk/config.py`**

```python
# src/vos_workbench/sdk/config.py
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ConfigAccessor(Protocol):
    """Access the module's validated, typed config. Injected via ModuleContext."""

    def get(self) -> Any: ...
```

- [ ] **Step 6: Implement `vos_workbench/sdk/capabilities.py`**

```python
# src/vos_workbench/sdk/capabilities.py
from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class CapabilityResolver(Protocol):
    """Resolve module instances by protocol. Cardinality-aware."""

    def resolve_one[T](self, protocol: type[T], *, selector: str | None = None) -> T:
        """Single instance. Raises if ambiguous without selector."""
        ...

    def resolve_all[T](self, protocol: type[T]) -> list[T]:
        """All instances implementing this protocol."""
        ...

    def resolve_named[T](self, protocol: type[T], instance_id: str | UUID) -> T:
        """Specific instance by UUID or module name."""
        ...
```

- [ ] **Step 7: Implement `vos_workbench/sdk/module_type.py`**

```python
# src/vos_workbench/sdk/module_type.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vos_workbench.sdk.context import ModuleContext
    from vos_workbench.sdk.manifest import ModuleManifest


@runtime_checkable
class ModuleType(Protocol):
    """Protocol that all module type classes must satisfy.

    Registered via vos.modules entry points. The spine discovers these at startup.
    type_name and version are class-level. config_model declares the Pydantic model
    for this module's config — the spine validates raw YAML against it.
    """

    type_name: str
    version: str
    config_model: type[Any]
    manifest: ModuleManifest

    async def start(self, context: ModuleContext) -> None: ...
    async def stop(self) -> None: ...
    async def health(self) -> dict[str, Any]: ...
```

- [ ] **Step 8: Implement `vos_workbench/sdk/context.py`**

```python
# src/vos_workbench/sdk/context.py
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vos_workbench.sdk.capabilities import CapabilityResolver
    from vos_workbench.sdk.config import ConfigAccessor
    from vos_workbench.sdk.events import EventPublisher


@dataclass(frozen=True)
class ModuleContext:
    """Injected into a module instance at start(). The module's only handle to the spine.

    Bundles all services a module is allowed to use. Modules must never import
    spine internals beyond vos_workbench.sdk.*.
    """

    module_name: str
    module_uuid: str
    publisher: EventPublisher
    config: ConfigAccessor
    capabilities: CapabilityResolver
```

- [ ] **Step 9: Implement `vos_workbench/sdk/__init__.py`**

```python
# src/vos_workbench/sdk/__init__.py
"""Spine SDK — the only vos_workbench surface that runtime modules may import."""

from vos_workbench.sdk.capabilities import CapabilityResolver
from vos_workbench.sdk.config import ConfigAccessor
from vos_workbench.sdk.context import ModuleContext
from vos_workbench.sdk.events import EventPublisher
from vos_workbench.sdk.manifest import ModuleManifest
from vos_workbench.sdk.module_type import ModuleType

__all__ = [
    "CapabilityResolver",
    "ConfigAccessor",
    "EventPublisher",
    "ModuleContext",
    "ModuleManifest",
    "ModuleType",
]
```

- [ ] **Step 10: Run tests**

```bash
uv run pytest tests/vos_workbench/test_sdk.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 11: Run lint**

```bash
uv run ruff check src/vos_workbench/sdk/ tests/vos_workbench/test_sdk.py
```

Expected: Clean.

- [ ] **Step 12: Commit**

```bash
git add src/vos_workbench/sdk/ tests/vos_workbench/test_sdk.py
git commit -m "feat: add spine SDK — public module-facing protocol boundary

ModuleType, ModuleManifest, ModuleContext, EventPublisher, ConfigAccessor,
CapabilityResolver. Runtime modules import only from vos_workbench.sdk.*."
```

---

## Task 3: Create contractkit — Module Interaction Protocols

**Files:**
- Create: `src/vos/contractkit/__init__.py`
- Create: `src/vos/contractkit/collector.py`
- Create: `src/vos/contractkit/merger.py`
- Create: `src/vos/contractkit/verifier.py`
- Create: `src/vos/contractkit/tracer.py`
- Create: `src/vos/contractkit/workflow.py`
- Create: `src/vos/contractkit/health.py`
- Test: `tests/contractkit/__init__.py`
- Test: `tests/contractkit/test_protocols.py`

Note: `src/vos/` must NOT have an `__init__.py` — implicit namespace package.

- [ ] **Step 1: Write failing tests**

```python
# tests/contractkit/test_protocols.py
from __future__ import annotations

from typing import Any

from vos.contractkit import (
    CollectorProtocol,
    MergerProtocol,
    ModuleHealth,
    ModuleStatus,
    PreflightWorkflowProtocol,
    TracerProtocol,
    VerifierProtocol,
)


class FakeCollector:
    async def collect(self) -> list[Any]:
        return []


class FakeMerger:
    async def merge(self, observations: list[Any]) -> tuple[Any, list[Any]]:
        return {}, []


class FakeVerifier:
    async def verify(self, declared: Any, observed: Any) -> Any:
        return {}


class FakeTracer:
    async def trace(self, snapshot: Any, request: Any) -> Any:
        return {}

    async def preview(self, snapshot: Any, request: Any) -> Any:
        return {}


class FakeWorkflow:
    async def run_verification(self) -> Any:
        return {}

    async def run_trace(self, request: Any) -> Any:
        return {}

    async def run_impact_preview(self, request: Any) -> Any:
        return {}


def test_collector_protocol():
    assert isinstance(FakeCollector(), CollectorProtocol)


def test_merger_protocol():
    assert isinstance(FakeMerger(), MergerProtocol)


def test_verifier_protocol():
    assert isinstance(FakeVerifier(), VerifierProtocol)


def test_tracer_protocol():
    assert isinstance(FakeTracer(), TracerProtocol)


def test_workflow_protocol():
    assert isinstance(FakeWorkflow(), PreflightWorkflowProtocol)


def test_module_health():
    h = ModuleHealth(status="ok", message=None, details={})
    assert h.status == "ok"
    assert h.details == {}


def test_module_status():
    s = ModuleStatus(
        module_name="switchcraft-1",
        module_type="resource.switchcraft",
        health=ModuleHealth(status="degraded", message="timeout", details={}),
    )
    assert s.module_name == "switchcraft-1"
    assert s.health.status == "degraded"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/contractkit/test_protocols.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'vos.contractkit'`

- [ ] **Step 3: Create `src/vos/` directory (NO `__init__.py`)**

```bash
mkdir -p src/vos/contractkit
```

Verify: `src/vos/__init__.py` does NOT exist.

- [ ] **Step 4: Implement protocols and health models**

`src/vos/contractkit/collector.py`:
```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vos.modelkit.observation import Observation


@runtime_checkable
class CollectorProtocol(Protocol):
    """Adapter service interface: collect live state, return normalized observations."""

    async def collect(self) -> list[Any]: ...
```

`src/vos/contractkit/merger.py`:
```python
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MergerProtocol(Protocol):
    """Merge observations into a canonical topology snapshot."""

    async def merge(self, observations: list[Any]) -> tuple[Any, list[Any]]: ...
```

`src/vos/contractkit/verifier.py`:
```python
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class VerifierProtocol(Protocol):
    """Compare declared vs observed state. Pure evaluator."""

    async def verify(self, declared: Any, observed: Any) -> Any: ...
```

`src/vos/contractkit/tracer.py`:
```python
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TracerProtocol(Protocol):
    """VLAN trace and change impact preview. Explicit-input evaluator."""

    async def trace(self, snapshot: Any, request: Any) -> Any: ...
    async def preview(self, snapshot: Any, request: Any) -> Any: ...
```

`src/vos/contractkit/workflow.py`:
```python
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PreflightWorkflowProtocol(Protocol):
    """Workflow facade. interfacekit resolves this, never low-level modules."""

    async def run_verification(self) -> Any: ...
    async def run_trace(self, request: Any) -> Any: ...
    async def run_impact_preview(self, request: Any) -> Any: ...
```

`src/vos/contractkit/health.py`:
```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModuleHealth:
    """Standard health status shape for any module."""

    status: str  # "ok", "degraded", "error", "unknown"
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModuleStatus:
    """Operational status of a module instance."""

    module_name: str
    module_type: str
    health: ModuleHealth
```

`src/vos/contractkit/__init__.py`:
```python
"""contractkit — Module interaction protocols and capability manifests.

No logic, no I/O, no domain objects. Only defines how modules talk to each other.
Part of the core dependency base — must stay protocol-only.
"""

from vos.contractkit.collector import CollectorProtocol
from vos.contractkit.health import ModuleHealth, ModuleStatus
from vos.contractkit.merger import MergerProtocol
from vos.contractkit.tracer import TracerProtocol
from vos.contractkit.verifier import VerifierProtocol
from vos.contractkit.workflow import PreflightWorkflowProtocol

__all__ = [
    "CollectorProtocol",
    "MergerProtocol",
    "ModuleHealth",
    "ModuleStatus",
    "PreflightWorkflowProtocol",
    "TracerProtocol",
    "VerifierProtocol",
]
```

- [ ] **Step 5: Create `tests/contractkit/__init__.py`**

Empty file.

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/contractkit/test_protocols.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 7: Run lint**

```bash
uv run ruff check src/vos/contractkit/ tests/contractkit/
```

- [ ] **Step 8: Commit**

```bash
git add src/vos/contractkit/ tests/contractkit/
git commit -m "feat: add contractkit — module interaction protocols

CollectorProtocol, MergerProtocol, VerifierProtocol, TracerProtocol,
PreflightWorkflowProtocol, ModuleHealth, ModuleStatus. No logic, no I/O."
```

---

## Task 4: Create modelkit — Enums and Core Entities (Device, Port, Link)

**Files:**
- Create: `src/vos/modelkit/__init__.py`
- Create: `src/vos/modelkit/enums.py`
- Create: `src/vos/modelkit/device.py`
- Create: `src/vos/modelkit/port.py`
- Create: `src/vos/modelkit/link.py`
- Create: `src/vos/modelkit/vlan.py`
- Test: `tests/modelkit/__init__.py`
- Test: `tests/modelkit/test_enums.py`
- Test: `tests/modelkit/test_device.py`
- Test: `tests/modelkit/test_port.py`
- Test: `tests/modelkit/test_link.py`

- [ ] **Step 1: Write failing tests for enums**

```python
# tests/modelkit/test_enums.py
from vos.modelkit.enums import (
    DeviceType,
    LinkType,
    ObservationSource,
    PortType,
    VlanMode,
)


def test_device_types():
    assert DeviceType.SWITCH == "switch"
    assert DeviceType.PROXMOX == "proxmox"
    assert DeviceType.FIREWALL == "firewall"
    assert DeviceType.VM == "vm"
    assert DeviceType.CONTAINER == "container"


def test_port_types():
    assert PortType.SFP_PLUS == "sfp+"
    assert PortType.ETHERNET == "ethernet"
    assert PortType.BRIDGE == "bridge"
    assert PortType.VLAN == "vlan"
    assert PortType.VIRTUAL == "virtual"


def test_link_types():
    assert LinkType.PHYSICAL_CABLE == "physical_cable"
    assert LinkType.BRIDGE_MEMBER == "bridge_member"
    assert LinkType.VLAN_PARENT == "vlan_parent"
    assert LinkType.INTERNAL_VIRTUAL == "internal_virtual"


def test_observation_sources():
    assert ObservationSource.MCP_LIVE == "mcp_live"
    assert ObservationSource.DECLARED == "declared"
    assert ObservationSource.INFERRED == "inferred"
    assert ObservationSource.UNKNOWN == "unknown"


def test_vlan_modes():
    assert VlanMode.TRUNK == "trunk"
    assert VlanMode.ACCESS == "access"
```

- [ ] **Step 2: Write failing tests for Device, Port, Link**

```python
# tests/modelkit/test_device.py
import pytest
from pydantic import ValidationError

from vos.modelkit.device import Device, Position
from vos.modelkit.enums import DeviceType


def test_device_minimal():
    d = Device(id="onti-be", name="ONTi-BE", type=DeviceType.SWITCH)
    assert d.id == "onti-be"
    assert d.name == "ONTi-BE"
    assert d.type == DeviceType.SWITCH
    assert d.ports == {}
    assert d.children == []


def test_device_full():
    d = Device(
        id="onti-be",
        name="ONTi-BE",
        type=DeviceType.SWITCH,
        model="S508CL-8S",
        management_ip="192.168.254.31",
        mcp_source="switchcraft:onti-backend",
        position=Position(x=400, y=200),
        children=["vm-100"],
    )
    assert d.model == "S508CL-8S"
    assert d.management_ip == "192.168.254.31"
    assert d.position.x == 400


def test_device_id_must_be_slug():
    with pytest.raises(ValidationError):
        Device(id="INVALID SLUG!", name="Bad", type=DeviceType.SWITCH)


def test_position():
    p = Position(x=100, y=200)
    assert p.x == 100
    assert p.y == 200
```

```python
# tests/modelkit/test_port.py
import pytest
from pydantic import ValidationError

from vos.modelkit.enums import PortType, VlanMode
from vos.modelkit.port import ExpectedNeighbor, Port, VlanMembership


def test_port_minimal():
    p = Port(type=PortType.SFP_PLUS)
    assert p.type == PortType.SFP_PLUS
    assert p.vlans is None
    assert p.expected_neighbor is None


def test_port_with_trunk_vlans():
    p = Port(
        type=PortType.SFP_PLUS,
        device_name="Ethernet1/0/1",
        speed="10G",
        description="Uplink to OPNsense",
        vlans=VlanMembership(mode=VlanMode.TRUNK, native=1, tagged=[25, 254]),
    )
    assert p.vlans.mode == VlanMode.TRUNK
    assert p.vlans.tagged == [25, 254]


def test_port_with_access_vlan():
    p = Port(
        type=PortType.ETHERNET,
        vlans=VlanMembership(mode=VlanMode.ACCESS, access_vlan=254),
    )
    assert p.vlans.access_vlan == 254


def test_expected_neighbor():
    n = ExpectedNeighbor(device="opnsense", port="ix1", mac="20:7C:14:F4:78:77")
    assert n.device == "opnsense"
    assert n.mac == "20:7C:14:F4:78:77"


def test_expected_neighbor_no_mac():
    n = ExpectedNeighbor(device="91tsm", port="port8")
    assert n.mac is None
```

```python
# tests/modelkit/test_link.py
from vos.modelkit.enums import LinkType
from vos.modelkit.link import Link, LinkEndpoint


def test_link_physical_cable():
    link = Link(
        id="phys-opnsense-ix1-to-onti-be-eth1",
        type=LinkType.PHYSICAL_CABLE,
        endpoints=(
            LinkEndpoint(device="opnsense", port="ix1"),
            LinkEndpoint(device="onti-be", port="eth1"),
        ),
        media="DAC SFP+ 0.5m",
        cable_color="black",
    )
    assert link.type == LinkType.PHYSICAL_CABLE
    assert link.endpoints[0].device == "opnsense"
    assert link.endpoints[1].port == "eth1"
    assert link.media == "DAC SFP+ 0.5m"


def test_link_bridge_member():
    link = Link(
        id="bridge-hx310db-nic1-to-vmbr1",
        type=LinkType.BRIDGE_MEMBER,
        endpoints=(
            LinkEndpoint(device="pve-hx310-db", port="nic1"),
            LinkEndpoint(device="pve-hx310-db", port="vmbr1"),
        ),
    )
    assert link.type == LinkType.BRIDGE_MEMBER


def test_link_endpoint():
    ep = LinkEndpoint(device="onti-be", port="eth7")
    assert ep.device == "onti-be"
    assert ep.port == "eth7"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/modelkit/ -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement enums**

```python
# src/vos/modelkit/enums.py
from __future__ import annotations

from enum import StrEnum


class DeviceType(StrEnum):
    SWITCH = "switch"
    PROXMOX = "proxmox"
    FIREWALL = "firewall"
    VM = "vm"
    CONTAINER = "container"
    ACCESSPOINT = "accesspoint"
    OTHER = "other"


class PortType(StrEnum):
    SFP_PLUS = "sfp+"
    ETHERNET = "ethernet"
    BRIDGE = "bridge"
    VLAN = "vlan"
    VIRTUAL = "virtual"


class LinkType(StrEnum):
    PHYSICAL_CABLE = "physical_cable"
    BRIDGE_MEMBER = "bridge_member"
    VLAN_PARENT = "vlan_parent"
    INTERNAL_VIRTUAL = "internal_virtual"


class ObservationSource(StrEnum):
    MCP_LIVE = "mcp_live"
    DECLARED = "declared"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class VlanMode(StrEnum):
    TRUNK = "trunk"
    ACCESS = "access"
```

- [ ] **Step 5: Implement device.py**

```python
# src/vos/modelkit/device.py
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from vos.modelkit.enums import DeviceType

if TYPE_CHECKING:
    from vos.modelkit.port import Port


class Position(BaseModel, frozen=True):
    x: float
    y: float


class Device(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    name: str
    type: DeviceType
    model: str | None = None
    management_ip: str | None = None
    mcp_source: str | None = None
    position: Position | None = None
    ports: dict[str, Port] = Field(default_factory=dict)
    children: list[str] = Field(default_factory=list)
```

- [ ] **Step 6: Implement port.py**

```python
# src/vos/modelkit/port.py
from __future__ import annotations

from pydantic import BaseModel, Field

from vos.modelkit.enums import PortType, VlanMode


class VlanMembership(BaseModel, frozen=True):
    mode: VlanMode
    native: int | None = None
    tagged: list[int] = Field(default_factory=list)
    access_vlan: int | None = None


class ExpectedNeighbor(BaseModel, frozen=True):
    device: str
    port: str
    mac: str | None = None


class Port(BaseModel):
    type: PortType
    device_name: str | None = None
    speed: str | None = None
    mac: str | None = None
    description: str | None = None
    vlans: VlanMembership | None = None
    expected_neighbor: ExpectedNeighbor | None = None
```

- [ ] **Step 7: Implement link.py**

```python
# src/vos/modelkit/link.py
from __future__ import annotations

from pydantic import BaseModel

from vos.modelkit.enums import LinkType


class LinkEndpoint(BaseModel, frozen=True):
    device: str
    port: str


class Link(BaseModel):
    id: str
    type: LinkType
    endpoints: tuple[LinkEndpoint, LinkEndpoint]
    media: str | None = None
    cable_color: str | None = None
    notes: str | None = None
```

- [ ] **Step 8: Implement vlan.py**

```python
# src/vos/modelkit/vlan.py
from __future__ import annotations

from pydantic import BaseModel


class VlanMetadata(BaseModel, frozen=True):
    name: str
    color: str | None = None
    subnet: str | None = None
    gateway: str | None = None
```

- [ ] **Step 9: Create `src/vos/modelkit/__init__.py` and `tests/modelkit/__init__.py`**

```python
# src/vos/modelkit/__init__.py
"""modelkit — Canonical domain objects for network topology.

Owns all domain data types (the nouns). No spine dependency, no network I/O.
"""

from vos.modelkit.device import Device, Position
from vos.modelkit.enums import DeviceType, LinkType, ObservationSource, PortType, VlanMode
from vos.modelkit.link import Link, LinkEndpoint
from vos.modelkit.port import ExpectedNeighbor, Port, VlanMembership
from vos.modelkit.vlan import VlanMetadata

__all__ = [
    "Device",
    "DeviceType",
    "ExpectedNeighbor",
    "Link",
    "LinkEndpoint",
    "LinkType",
    "ObservationSource",
    "Port",
    "PortType",
    "Position",
    "VlanMembership",
    "VlanMetadata",
    "VlanMode",
]
```

`tests/modelkit/__init__.py`: empty file.

- [ ] **Step 10: Run tests**

```bash
uv run pytest tests/modelkit/ -v
```

Expected: All tests PASS.

- [ ] **Step 11: Run lint**

```bash
uv run ruff check src/vos/modelkit/ tests/modelkit/
```

- [ ] **Step 12: Commit**

```bash
git add src/vos/modelkit/ tests/modelkit/
git commit -m "feat: add modelkit — core domain models (Device, Port, Link, VLAN)

Enums for DeviceType, PortType, LinkType, ObservationSource, VlanMode.
Pydantic v2 models for Device, Port, VlanMembership, ExpectedNeighbor,
Link, LinkEndpoint, VlanMetadata, Position."
```

---

## Task 5: Create modelkit — Derived Models (Topology, Observation, Verification, Trace, Impact)

**Files:**
- Create: `src/vos/modelkit/topology.py`
- Create: `src/vos/modelkit/observation.py`
- Create: `src/vos/modelkit/verification.py`
- Create: `src/vos/modelkit/trace.py`
- Create: `src/vos/modelkit/impact.py`
- Test: `tests/modelkit/test_topology.py`
- Test: `tests/modelkit/test_observation.py`
- Test: `tests/modelkit/test_verification.py`
- Test: `tests/modelkit/test_trace.py`
- Test: `tests/modelkit/test_impact.py`
- Modify: `src/vos/modelkit/__init__.py` (add new exports)

- [ ] **Step 1: Write failing tests for TopologySnapshot**

```python
# tests/modelkit/test_topology.py
from vos.modelkit.device import Device, Position
from vos.modelkit.enums import DeviceType, LinkType, PortType, VlanMode
from vos.modelkit.link import Link, LinkEndpoint
from vos.modelkit.port import Port, VlanMembership
from vos.modelkit.topology import TopologyMeta, TopologySnapshot
from vos.modelkit.vlan import VlanMetadata


def test_topology_meta():
    m = TopologyMeta(version="1.0", name="VOS Network")
    assert m.version == "1.0"
    assert m.updated_by is None


def test_topology_snapshot_empty():
    snap = TopologySnapshot(
        meta=TopologyMeta(version="1.0", name="Test"),
        devices={},
        links=[],
        vlans={},
    )
    assert snap.devices == {}
    assert snap.links == []


def test_topology_snapshot_with_data():
    snap = TopologySnapshot(
        meta=TopologyMeta(version="1.0", name="VOS"),
        devices={
            "onti-be": Device(
                id="onti-be",
                name="ONTi-BE",
                type=DeviceType.SWITCH,
                ports={
                    "eth1": Port(
                        type=PortType.SFP_PLUS,
                        vlans=VlanMembership(mode=VlanMode.TRUNK, tagged=[25, 254]),
                    ),
                },
            ),
        },
        links=[
            Link(
                id="phys-1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="onti-be", port="eth1"),
                    LinkEndpoint(device="opnsense", port="ix1"),
                ),
            ),
        ],
        vlans={"254": VlanMetadata(name="Management", color="#2196F3")},
    )
    assert "onti-be" in snap.devices
    assert len(snap.links) == 1
    assert "254" in snap.vlans
```

- [ ] **Step 2: Write failing tests for Observation, Mismatch, MergeConflict**

```python
# tests/modelkit/test_observation.py
from vos.modelkit.enums import ObservationSource
from vos.modelkit.observation import MergeConflict, Mismatch, Observation


def test_observation():
    obs = Observation(
        device="onti-be",
        port="eth7",
        field="link_status",
        value="down",
        source=ObservationSource.MCP_LIVE,
    )
    assert obs.device == "onti-be"
    assert obs.source == ObservationSource.MCP_LIVE


def test_observation_with_adapter():
    obs = Observation(
        device="onti-be",
        port="eth1",
        field="mac_table",
        value=["20:7C:14:F4:78:77"],
        source=ObservationSource.MCP_LIVE,
        adapter="switchcraft",
    )
    assert obs.adapter == "switchcraft"


def test_mismatch():
    m = Mismatch(
        device="onti-be",
        port="eth7",
        field="link_status",
        expected="up",
        observed="down",
        source=ObservationSource.MCP_LIVE,
        severity="error",
    )
    assert m.expected == "up"
    assert m.observed == "down"
    assert m.severity == "error"


def test_merge_conflict():
    mc = MergeConflict(
        device="onti-be",
        port="eth1",
        field="mac_table",
        sources=["switchcraft", "proxmoxcraft"],
        values=[["aa:bb:cc:dd:ee:ff"], ["11:22:33:44:55:66"]],
        resolution="first_source",
    )
    assert len(mc.sources) == 2
```

- [ ] **Step 3: Write failing tests for VerificationReport**

```python
# tests/modelkit/test_verification.py
from vos.modelkit.enums import ObservationSource
from vos.modelkit.verification import CheckResult, LinkVerification, VerificationReport


def test_check_result():
    cr = CheckResult(
        check="link_status",
        port="onti-be:eth7",
        expected="up",
        observed="down",
        source=ObservationSource.MCP_LIVE,
        flag="error",
    )
    assert cr.check == "link_status"
    assert cr.flag == "error"


def test_link_verification():
    lv = LinkVerification(
        link="phys-onti-be-eth7-to-hx310db-nic1",
        link_type="physical_cable",
        status="fail",
        checks=[
            CheckResult(
                check="link_status",
                port="onti-be:eth7",
                expected="up",
                observed="down",
                source=ObservationSource.MCP_LIVE,
                flag="error",
            ),
        ],
    )
    assert lv.status == "fail"
    assert len(lv.checks) == 1


def test_verification_report():
    report = VerificationReport(
        results=[],
        summary={"total_links": 0, "ok": 0, "warn": 0, "fail": 0},
    )
    assert report.summary["total_links"] == 0
```

- [ ] **Step 4: Write failing tests for TraceRequest/Result**

```python
# tests/modelkit/test_trace.py
from vos.modelkit.enums import ObservationSource
from vos.modelkit.trace import BreakPoint, TraceHop, TraceRequest, TraceResult


def test_trace_request():
    req = TraceRequest(vlan=254, source="opnsense", target="pve-hx310-db")
    assert req.vlan == 254


def test_trace_request_vlan_only():
    req = TraceRequest(vlan=254)
    assert req.source is None
    assert req.target is None


def test_trace_hop():
    hop = TraceHop(
        device="opnsense",
        port="bridge0",
        status="ok",
        source=ObservationSource.MCP_LIVE,
    )
    assert hop.status == "ok"


def test_trace_hop_with_link():
    hop = TraceHop(
        link="phys-opnsense-ix1-to-onti-be-eth1",
        status="ok",
        source=ObservationSource.MCP_LIVE,
    )
    assert hop.link is not None
    assert hop.device is None


def test_break_point():
    bp = BreakPoint(
        device="onti-be",
        port="eth7",
        reason="link down, expected MAC absent",
        likely_causes=["missing SFP module", "bad cable"],
    )
    assert len(bp.likely_causes) == 2


def test_trace_result():
    result = TraceResult(
        vlan=254,
        source="opnsense",
        target="pve-hx310-db",
        status="broken",
        hops=[],
        first_break=BreakPoint(
            device="onti-be",
            port="eth7",
            reason="link down",
            likely_causes=[],
        ),
    )
    assert result.status == "broken"
    assert result.first_break is not None
```

- [ ] **Step 5: Write failing tests for ImpactRequest/Result**

```python
# tests/modelkit/test_impact.py
from vos.modelkit.impact import ImpactEffect, ImpactRequest, ImpactResult


def test_impact_request():
    req = ImpactRequest(
        action="remove_vlan",
        device="onti-be",
        port="eth7",
        parameters={"vlan": 254},
    )
    assert req.action == "remove_vlan"
    assert req.parameters["vlan"] == 254


def test_impact_effect():
    eff = ImpactEffect(
        device="pve-hx310-db",
        port="nic1",
        effect="loses VLAN 254 on backend path",
        severity="high",
    )
    assert eff.severity == "high"


def test_impact_result():
    result = ImpactResult(
        proposed_change=ImpactRequest(
            action="remove_vlan",
            device="onti-be",
            port="eth7",
            parameters={"vlan": 254},
        ),
        impact=[
            ImpactEffect(
                device="pve-hx310-db",
                port="nic1",
                effect="loses VLAN 254",
                severity="high",
            ),
        ],
        risk="high",
        safe_to_apply=False,
    )
    assert not result.safe_to_apply
    assert result.risk == "high"
    assert len(result.impact) == 1
```

- [ ] **Step 6: Run all modelkit tests to verify they fail**

```bash
uv run pytest tests/modelkit/ -v
```

Expected: FAIL on new test files.

- [ ] **Step 7: Implement topology.py**

```python
# src/vos/modelkit/topology.py
from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any

from pydantic import BaseModel, Field

from vos.modelkit.device import Device
from vos.modelkit.link import Link
from vos.modelkit.vlan import VlanMetadata


class TopologyMeta(BaseModel, frozen=True):
    version: str
    name: str
    updated: datetime | None = None
    updated_by: str | None = None


class TopologySnapshot(BaseModel):
    meta: TopologyMeta
    devices: dict[str, Device] = Field(default_factory=dict)
    links: list[Link] = Field(default_factory=list)
    vlans: dict[str, VlanMetadata] = Field(default_factory=dict)
```

- [ ] **Step 8: Implement observation.py**

```python
# src/vos/modelkit/observation.py
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from vos.modelkit.enums import ObservationSource


class Observation(BaseModel):
    device: str
    port: str | None = None
    field: str
    value: Any
    source: ObservationSource
    adapter: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Mismatch(BaseModel):
    device: str
    port: str | None = None
    field: str
    expected: Any
    observed: Any
    source: ObservationSource
    severity: str = "error"
    message: str | None = None


class MergeConflict(BaseModel):
    device: str
    port: str | None = None
    field: str
    sources: list[str]
    values: list[Any]
    resolution: str | None = None
```

- [ ] **Step 9: Implement verification.py**

```python
# src/vos/modelkit/verification.py
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from vos.modelkit.enums import ObservationSource


class CheckResult(BaseModel):
    check: str
    port: str
    expected: Any
    observed: Any
    source: ObservationSource
    flag: str  # "ok", "warning", "error"
    message: str | None = None


class LinkVerification(BaseModel):
    link: str
    link_type: str
    status: str  # "ok", "warn", "fail"
    checks: list[CheckResult] = Field(default_factory=list)


class VerificationReport(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    results: list[LinkVerification] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)
```

- [ ] **Step 10: Implement trace.py**

```python
# src/vos/modelkit/trace.py
from __future__ import annotations

from pydantic import BaseModel, Field

from vos.modelkit.enums import ObservationSource


class TraceRequest(BaseModel, frozen=True):
    vlan: int
    source: str | None = None
    target: str | None = None


class TraceHop(BaseModel):
    device: str | None = None
    port: str | None = None
    link: str | None = None
    status: str  # "ok", "fail", "unknown"
    source: ObservationSource
    reason: str | None = None


class BreakPoint(BaseModel, frozen=True):
    device: str
    port: str
    reason: str
    likely_causes: list[str] = Field(default_factory=list)


class TraceResult(BaseModel):
    vlan: int
    source: str | None = None
    target: str | None = None
    status: str  # "ok", "broken"
    hops: list[TraceHop] = Field(default_factory=list)
    first_break: BreakPoint | None = None
```

- [ ] **Step 11: Implement impact.py**

```python
# src/vos/modelkit/impact.py
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ImpactRequest(BaseModel, frozen=True):
    action: str
    device: str
    port: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class ImpactEffect(BaseModel):
    device: str
    port: str | None = None
    effect: str
    severity: str  # "low", "medium", "high"


class ImpactResult(BaseModel):
    proposed_change: ImpactRequest
    impact: list[ImpactEffect] = Field(default_factory=list)
    risk: str  # "low", "medium", "high"
    safe_to_apply: bool
```

- [ ] **Step 12: Update `src/vos/modelkit/__init__.py` with new exports**

Add to existing `__init__.py`:

```python
from vos.modelkit.impact import ImpactEffect, ImpactRequest, ImpactResult
from vos.modelkit.observation import MergeConflict, Mismatch, Observation
from vos.modelkit.topology import TopologyMeta, TopologySnapshot
from vos.modelkit.trace import BreakPoint, TraceHop, TraceRequest, TraceResult
from vos.modelkit.verification import CheckResult, LinkVerification, VerificationReport
```

And add to `__all__`:

```python
    "BreakPoint",
    "CheckResult",
    "ImpactEffect",
    "ImpactRequest",
    "ImpactResult",
    "LinkVerification",
    "MergeConflict",
    "Mismatch",
    "Observation",
    "TopologyMeta",
    "TopologySnapshot",
    "TraceHop",
    "TraceRequest",
    "TraceResult",
    "VerificationReport",
```

- [ ] **Step 13: Run all modelkit tests**

```bash
uv run pytest tests/modelkit/ -v
```

Expected: All tests PASS.

- [ ] **Step 14: Run lint**

```bash
uv run ruff check src/vos/modelkit/ tests/modelkit/
```

- [ ] **Step 15: Commit**

```bash
git add src/vos/modelkit/ tests/modelkit/
git commit -m "feat: add modelkit derived models — topology, observation, verification, trace, impact

TopologySnapshot, TopologyMeta, Observation, Mismatch, MergeConflict,
VerificationReport, CheckResult, LinkVerification, TraceRequest/Result,
BreakPoint, TraceHop, ImpactRequest/Result/Effect."
```

---

## Task 6: Create graphkit and storekit Stubs

**Files:**
- Create: `src/vos/graphkit/__init__.py`
- Create: `src/vos/storekit/__init__.py`

- [ ] **Step 1: Create graphkit stub**

```python
# src/vos/graphkit/__init__.py
"""graphkit — Graph traversal on topology snapshots.

Pure library. Neighbors, BFS/DFS, subgraph extraction, VLAN filtering.
Depends on: contractkit, modelkit. No spine dependency, no network I/O.
"""
```

- [ ] **Step 2: Create storekit stub**

```python
# src/vos/storekit/__init__.py
"""storekit — Topology snapshot serialization, schema versioning, diff.

Pure library. Load/save topology.json, schema migration, import/export, diffing.
Depends on: contractkit, modelkit. No spine dependency, no network I/O
(local file I/O for topology snapshots by design — no DB, no MCP).
"""
```

- [ ] **Step 3: Commit**

```bash
git add src/vos/graphkit/ src/vos/storekit/
git commit -m "feat: add graphkit and storekit stubs (pure library placeholders)"
```

---

## Task 7: Create Runtime Module Stubs

**Files:**
- Create: `src/vos/switchcraft/__init__.py`
- Create: `src/vos/opnsensecraft/__init__.py`
- Create: `src/vos/proxmoxcraft/__init__.py`
- Create: `src/vos/collectkit/__init__.py`
- Create: `src/vos/verifykit/__init__.py`
- Create: `src/vos/tracekit/__init__.py`
- Create: `src/vos/interfacekit/__init__.py`
- Test: `tests/stubs/test_module_stubs.py`

Each runtime module stub declares a module class with `type_name`, `version`, `config_model`, `manifest`, and no-op lifecycle methods. This proves they satisfy the `ModuleType` protocol.

- [ ] **Step 1: Write failing test for all module stubs**

```python
# tests/stubs/__init__.py
```

```python
# tests/stubs/test_module_stubs.py
from __future__ import annotations

from vos_workbench.sdk import ModuleType


def test_switchcraft_module_type():
    from vos.switchcraft import SwitchcraftModule

    assert isinstance(SwitchcraftModule(), ModuleType)
    assert SwitchcraftModule.type_name == "resource.switchcraft"


def test_opnsensecraft_module_type():
    from vos.opnsensecraft import OpnsensecraftModule

    assert isinstance(OpnsensecraftModule(), ModuleType)
    assert OpnsensecraftModule.type_name == "resource.opnsensecraft"


def test_proxmoxcraft_module_type():
    from vos.proxmoxcraft import ProxmoxcraftModule

    assert isinstance(ProxmoxcraftModule(), ModuleType)
    assert ProxmoxcraftModule.type_name == "resource.proxmoxcraft"


def test_collectkit_module_type():
    from vos.collectkit import CollectkitModule

    assert isinstance(CollectkitModule(), ModuleType)
    assert CollectkitModule.type_name == "resource.collectkit"


def test_verifykit_module_type():
    from vos.verifykit import VerifykitModule

    assert isinstance(VerifykitModule(), ModuleType)
    assert VerifykitModule.type_name == "core.verifykit"


def test_tracekit_module_type():
    from vos.tracekit import TracekitModule

    assert isinstance(TracekitModule(), ModuleType)
    assert TracekitModule.type_name == "core.tracekit"


def test_interfacekit_module_type():
    from vos.interfacekit import InterfacekitModule

    assert isinstance(InterfacekitModule(), ModuleType)
    assert InterfacekitModule.type_name == "integration.interfacekit"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/stubs/ -v
```

Expected: FAIL.

- [ ] **Step 3: Implement all module stubs**

Each follows the same pattern. Here is the template, then the specifics:

```python
# src/vos/switchcraft/__init__.py
"""switchcraft — Switch adapter module.

Collects live state from managed switches (telnet/HTTP), normalizes to observations.
Runtime module: registers via vos.modules entry point.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from vos_workbench.sdk import ModuleContext, ModuleManifest


class SwitchcraftConfig(BaseModel):
    host: str
    port: int = 23
    transport: str = "telnet"


class SwitchcraftModule:
    type_name = "resource.switchcraft"
    version = "0.1.0"
    config_model = SwitchcraftConfig
    manifest = ModuleManifest(
        capabilities_provided=["collect"],
        capabilities_required=[],
    )

    async def start(self, context: ModuleContext) -> None:
        self._context = context

    async def stop(self) -> None:
        pass

    async def health(self) -> dict[str, Any]:
        return {"status": "ok"}
```

```python
# src/vos/opnsensecraft/__init__.py
"""opnsensecraft — OPNsense adapter module.

Collects live state from OPNsense (MCP/API), normalizes to observations.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from vos_workbench.sdk import ModuleContext, ModuleManifest


class OpnsensecraftConfig(BaseModel):
    host: str
    api_key: str = ""
    api_secret: str = ""


class OpnsensecraftModule:
    type_name = "resource.opnsensecraft"
    version = "0.1.0"
    config_model = OpnsensecraftConfig
    manifest = ModuleManifest(
        capabilities_provided=["collect"],
        capabilities_required=[],
    )

    async def start(self, context: ModuleContext) -> None:
        self._context = context

    async def stop(self) -> None:
        pass

    async def health(self) -> dict[str, Any]:
        return {"status": "ok"}
```

```python
# src/vos/proxmoxcraft/__init__.py
"""proxmoxcraft — Proxmox adapter module.

Collects live state from Proxmox (MCP/API), normalizes to observations.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from vos_workbench.sdk import ModuleContext, ModuleManifest


class ProxmoxcraftConfig(BaseModel):
    host: str
    user: str = "root@pam"
    token_name: str = ""
    token_value: str = ""


class ProxmoxcraftModule:
    type_name = "resource.proxmoxcraft"
    version = "0.1.0"
    config_model = ProxmoxcraftConfig
    manifest = ModuleManifest(
        capabilities_provided=["collect"],
        capabilities_required=[],
    )

    async def start(self, context: ModuleContext) -> None:
        self._context = context

    async def stop(self) -> None:
        pass

    async def health(self) -> dict[str, Any]:
        return {"status": "ok"}
```

```python
# src/vos/collectkit/__init__.py
"""collectkit — Normalize and merge live observations into topology snapshot.

Accepts observations from adapters, normalizes, merges, emits conflicts.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from vos_workbench.sdk import ModuleContext, ModuleManifest


class CollectkitConfig(BaseModel):
    merge_strategy: str = "first_source"


class CollectkitModule:
    type_name = "resource.collectkit"
    version = "0.1.0"
    config_model = CollectkitConfig
    manifest = ModuleManifest(
        capabilities_provided=["merge"],
        capabilities_required=["collect"],
    )

    async def start(self, context: ModuleContext) -> None:
        self._context = context

    async def stop(self) -> None:
        pass

    async def health(self) -> dict[str, Any]:
        return {"status": "ok"}
```

```python
# src/vos/verifykit/__init__.py
"""verifykit — Verification engine.

Compares declared vs observed state. Pure evaluator: two snapshots in, report out.
Never loads files, never queries DB, never calls adapters.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from vos_workbench.sdk import ModuleContext, ModuleManifest


class VerifykitConfig(BaseModel):
    pass


class VerifykitModule:
    type_name = "core.verifykit"
    version = "0.1.0"
    config_model = VerifykitConfig
    manifest = ModuleManifest(
        capabilities_provided=["verify"],
        capabilities_required=[],
    )

    async def start(self, context: ModuleContext) -> None:
        self._context = context

    async def stop(self) -> None:
        pass

    async def health(self) -> dict[str, Any]:
        return {"status": "ok"}
```

```python
# src/vos/tracekit/__init__.py
"""tracekit — VLAN trace, break detection, impact preview.

Explicit-input evaluator: receives TopologySnapshot, never loads its own state.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from vos_workbench.sdk import ModuleContext, ModuleManifest


class TracekitConfig(BaseModel):
    pass


class TracekitModule:
    type_name = "core.tracekit"
    version = "0.1.0"
    config_model = TracekitConfig
    manifest = ModuleManifest(
        capabilities_provided=["trace", "preview"],
        capabilities_required=[],
    )

    async def start(self, context: ModuleContext) -> None:
        self._context = context

    async def stop(self) -> None:
        pass

    async def health(self) -> dict[str, Any]:
        return {"status": "ok"}
```

```python
# src/vos/interfacekit/__init__.py
"""interfacekit — API routes, MCP exposure, DTO mapping.

Resolves PreflightWorkflowProtocol via capability resolver. Never touches
low-level modules directly.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from vos_workbench.sdk import ModuleContext, ModuleManifest


class InterfacekitConfig(BaseModel):
    api_prefix: str = "/api/v1"


class InterfacekitModule:
    type_name = "integration.interfacekit"
    version = "0.1.0"
    config_model = InterfacekitConfig
    manifest = ModuleManifest(
        capabilities_provided=["http_api", "mcp_tools"],
        capabilities_required=["preflight_workflow"],
    )

    async def start(self, context: ModuleContext) -> None:
        self._context = context

    async def stop(self) -> None:
        pass

    async def health(self) -> dict[str, Any]:
        return {"status": "ok"}
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/stubs/ -v
```

Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vos/switchcraft/ src/vos/opnsensecraft/ src/vos/proxmoxcraft/ \
    src/vos/collectkit/ src/vos/verifykit/ src/vos/tracekit/ src/vos/interfacekit/ \
    tests/stubs/
git commit -m "feat: add runtime module stubs — all satisfy ModuleType protocol

switchcraft, opnsensecraft, proxmoxcraft, collectkit, verifykit, tracekit,
interfacekit. Each declares type_name, version, config_model, manifest."
```

---

## Task 8: Create App Shell Stub and Entry Points

**Files:**
- Create: `src/vos/apps/__init__.py`
- Create: `src/vos/apps/preflight/__init__.py`
- Modify: `pyproject.toml` (add entry points)

- [ ] **Step 1: Create apps namespace and preflight stub**

```python
# src/vos/apps/__init__.py
```

```python
# src/vos/apps/preflight/__init__.py
"""preflight — Thin workflow composition shell.

Implements PreflightWorkflowProtocol. Orchestrates: collect -> merge -> verify
-> trace -> expose. Contains almost zero domain logic — all work delegated to
modules via contractkit protocols.
"""
```

- [ ] **Step 2: Add entry points to pyproject.toml**

Update the `[project.entry-points."vos.modules"]` section:

```toml
[project.entry-points."vos.modules"]
"resource.switchcraft" = "vos.switchcraft:SwitchcraftModule"
"resource.opnsensecraft" = "vos.opnsensecraft:OpnsensecraftModule"
"resource.proxmoxcraft" = "vos.proxmoxcraft:ProxmoxcraftModule"
"resource.collectkit" = "vos.collectkit:CollectkitModule"
"core.verifykit" = "vos.verifykit:VerifykitModule"
"core.tracekit" = "vos.tracekit:TracekitModule"
"integration.interfacekit" = "vos.interfacekit:InterfacekitModule"
```

- [ ] **Step 3: Reinstall package (entry points require reinstall)**

```bash
uv pip install -e ".[dev]"
```

- [ ] **Step 4: Test entry point discovery**

```python
# tests/stubs/test_entry_points.py
from importlib.metadata import entry_points


def test_vos_modules_entry_points_registered():
    eps = entry_points(group="vos.modules")
    names = {ep.name for ep in eps}
    expected = {
        "resource.switchcraft",
        "resource.opnsensecraft",
        "resource.proxmoxcraft",
        "resource.collectkit",
        "core.verifykit",
        "core.tracekit",
        "integration.interfacekit",
    }
    assert expected.issubset(names), f"Missing: {expected - names}"


def test_entry_points_load():
    eps = entry_points(group="vos.modules")
    for ep in eps:
        module_type = ep.load()
        assert hasattr(module_type, "type_name")
        assert hasattr(module_type, "version")
        assert hasattr(module_type, "config_model")
```

- [ ] **Step 5: Run all tests**

```bash
uv run pytest tests/ -v
```

Expected: All tests PASS (existing spine tests + new SDK/contractkit/modelkit/stub tests).

- [ ] **Step 6: Commit**

```bash
git add src/vos/apps/ pyproject.toml tests/stubs/test_entry_points.py
git commit -m "feat: add preflight app shell stub and register module entry points

All 7 runtime modules registered under vos.modules entry point group.
Entry point discovery verified."
```

---

## Task 9: Update CLAUDE.md and Final Verification

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Write CLAUDE.md**

```markdown
# VOS-Ruggensgraat

## Project
Modular agentic backend with network topology verification. Alpha phase.
Merges VOS-Workbench spine with Preflight/NetMap domain modules.

## Authority
`docs/superpowers/specs/2026-04-07-ruggensgraat-architecture-design.md` is the authoritative architecture spec.

## Commands
- **Lint:** `uv run ruff check src/ tests/`
- **Format:** `uv run ruff format src/ tests/`
- **Test:** `uv run pytest tests/ -v`
- **Type check:** `uv run pyright src/`
- **All checks:** `uv run ruff check src/ tests/ && uv run pytest tests/ -v && uv run pyright src/`

## Conventions
- Python 3.14, async-first
- Pydantic v2 for all data models
- FastAPI for API layer
- SQLModel for database models (spine only)
- structlog for logging
- YAML for config, Pydantic for validation
- ruff for lint+format, pytest with pytest-asyncio, TDD

## Code Style
- Line length: 100
- Type annotations on public functions
- No docstrings on obvious functions
- Prefer composition over inheritance
- Small focused files

## Package Structure
- `src/vos_workbench/` — runtime spine (unchanged, do NOT rename)
- `src/vos_workbench/sdk/` — public SDK for modules (the ONLY allowed spine import surface)
- `src/vos/` — implicit namespace package (NO __init__.py here)
- `src/vos/contractkit/` — module interaction protocols (no logic, no domain objects)
- `src/vos/modelkit/` — domain data types (Device, Port, Link, VLAN, etc.)
- `src/vos/graphkit/` — graph traversal (pure library)
- `src/vos/storekit/` — topology serialization (pure library)
- `src/vos/{switchcraft,opnsensecraft,proxmoxcraft}/` — adapter modules
- `src/vos/{collectkit,verifykit,tracekit,interfacekit}/` — engine modules
- `src/vos/apps/preflight/` — app shell

## Dependency Rules (HARD)
- `contractkit` → nothing
- Pure libraries (modelkit, graphkit, storekit) → contractkit only
- Runtime modules → pure libraries + contractkit + vos_workbench.sdk.*
- Apps → public module interfaces (contractkit protocols) + spine bootstrap
- NEVER import from vos_workbench.runtime, .storage, .events.bus, etc.
- NEVER import between adapter modules (switchcraft must not import opnsensecraft)

## Architecture Rules
- Service-primary interaction; events for audit/telemetry only
- verifykit and tracekit are pure evaluators with explicit inputs
- interfacekit resolves PreflightWorkflowProtocol, never low-level modules
- Module config is typed and validated before module code sees it
- One ModuleType can have multiple instances

## Git
- Check status before changes
- Suggest commits at logical points
- Never push without asking
- Never commit secrets
```

- [ ] **Step 2: Run full test suite**

```bash
uv run ruff check src/ tests/ && uv run pytest tests/ -v
```

Expected: All lint clean, all tests pass.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for VOS-Ruggensgraat architecture

Package structure, dependency rules, architecture rules, conventions."
```

- [ ] **Step 4: Final status check**

```bash
git log --oneline
```

Expected: 9+ commits showing the full scaffolding progression.
