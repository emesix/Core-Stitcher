from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from stitch_workbench.sdk.context import ModuleContext
    from stitch_workbench.sdk.manifest import ModuleManifest


@runtime_checkable
class ModuleType(Protocol):
    type_name: str
    version: str
    config_model: type[Any]
    manifest: ModuleManifest

    async def start(self, context: ModuleContext) -> None: ...
    async def stop(self) -> None: ...
    async def health(self) -> dict: ...
