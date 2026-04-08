from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from uuid import UUID


@runtime_checkable
class CapabilityResolver(Protocol):
    def resolve_one[T](self, protocol: type[T], *, selector: str | None = None) -> T: ...
    def resolve_all[T](self, protocol: type[T]) -> list[T]: ...
    def resolve_named[T](self, protocol: type[T], instance_id: str | UUID) -> T: ...
