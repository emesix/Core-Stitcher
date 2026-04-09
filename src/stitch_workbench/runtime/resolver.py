"""RuntimeCapabilityResolver — resolves protocols from started module instances.

First real implementation of the SDK's CapabilityResolver protocol. Maintains
a registry of started module instances and resolves them by checking which
protocols they implement (via isinstance/hasattr checks).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uuid import UUID


class AmbiguousCapabilityError(Exception):
    def __init__(self, protocol: type, count: int) -> None:
        super().__init__(
            f"Ambiguous capability: {count} instances implement "
            f"{protocol.__name__}. Use resolve_all() or provide a selector."
        )


class CapabilityNotFoundError(LookupError):
    def __init__(self, protocol: type, detail: str = "") -> None:
        msg = f"No capability found for {protocol.__name__}"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


class RuntimeCapabilityResolver:
    """Resolves capabilities from a set of started module instances.

    Each registered instance is checked against requested protocols using
    runtime_checkable Protocol isinstance checks.
    """

    def __init__(self) -> None:
        self._instances: dict[str, Any] = {}  # instance_id → module instance
        self._names: dict[str, str] = {}  # module_name → instance_id

    def register(
        self,
        instance: Any,
        *,
        instance_id: str,
        name: str | None = None,
    ) -> None:
        self._instances[instance_id] = instance
        if name:
            self._names[name] = instance_id

    def unregister(self, instance_id: str) -> None:
        self._instances.pop(instance_id, None)
        self._names = {n: iid for n, iid in self._names.items() if iid != instance_id}

    def resolve_one[T](self, protocol: type[T], *, selector: str | None = None) -> T:
        matches = self._find_all(protocol)

        if selector:
            matches = [
                (iid, inst)
                for iid, inst in matches
                if iid == selector or self._name_for(iid) == selector
            ]

        if len(matches) == 0:
            raise CapabilityNotFoundError(protocol, selector or "")
        if len(matches) > 1 and selector is None:
            raise AmbiguousCapabilityError(protocol, len(matches))

        return matches[0][1]

    def resolve_all[T](self, protocol: type[T]) -> list[T]:
        return [inst for _iid, inst in self._find_all(protocol)]

    def resolve_named[T](self, protocol: type[T], instance_id: str | UUID) -> T:
        iid = str(instance_id)
        inst = self._instances.get(iid)
        if inst is None:
            # Try by name
            mapped_id = self._names.get(iid)
            if mapped_id:
                inst = self._instances.get(mapped_id)

        if inst is None:
            raise CapabilityNotFoundError(protocol, f"instance '{iid}' not found")

        if not isinstance(inst, protocol):
            raise CapabilityNotFoundError(
                protocol, f"instance '{iid}' does not implement {protocol.__name__}"
            )

        return inst

    def _find_all(self, protocol: type) -> list[tuple[str, Any]]:
        return [(iid, inst) for iid, inst in self._instances.items() if isinstance(inst, protocol)]

    def _name_for(self, instance_id: str) -> str | None:
        for name, iid in self._names.items():
            if iid == instance_id:
                return name
        return None
