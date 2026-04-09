from __future__ import annotations

from typing import Any
from uuid import UUID

from stitch_workbench.sdk import (
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
    assert isinstance(FakePublisher(), EventPublisher)


def test_config_accessor_protocol():
    assert isinstance(FakeConfigAccessor(FakeConfig()), ConfigAccessor)


def test_capability_resolver_protocol():
    assert isinstance(FakeResolver(), CapabilityResolver)
