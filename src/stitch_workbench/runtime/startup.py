from __future__ import annotations

from dataclasses import dataclass, field
from graphlib import CycleError, TopologicalSorter
from typing import TYPE_CHECKING

import structlog

from vos_workbench.uri.parser import VosReference

if TYPE_CHECKING:
    from vos_workbench.config.models import ModuleConfig

logger = structlog.get_logger()


class CircularDependencyError(Exception):
    """Raised when module dependencies form a cycle."""


@dataclass
class StartupPlan:
    """Result of computing startup order."""

    order: list[list[str]]
    """Groups of module names that can start in parallel, in sequence."""

    failed: dict[str, str] = field(default_factory=dict)
    """Modules that cannot start, mapped to the reason."""


def compute_startup_order(modules: list[ModuleConfig]) -> StartupPlan:
    """Compute parallel startup groups using topological sort.

    Returns a StartupPlan with:
    - order: groups of modules that can start (sequentially by group, parallel within)
    - failed: modules that cannot start due to missing hard dependencies

    Rules:
    - Hard dependency missing/disabled at startup → dependent enters failed
    - Soft dependency missing/disabled → warn, dependent still starts
    - Disabled modules are excluded from the graph entirely
    - Cascading: if A hard-depends on B, and B is failed, A also fails
    """
    enabled = {mod.name: mod for mod in modules if mod.enabled}
    enabled_names = set(enabled.keys())

    failed: dict[str, str] = {}

    # First pass: identify modules with unsatisfied hard dependencies
    def _cascade_failures() -> bool:
        """Mark modules as failed if any hard dep is missing or itself failed.
        Returns True if new failures were found (need another pass)."""
        changed = False
        for mod in list(enabled.values()):
            if mod.name in failed:
                continue
            for dep in mod.wiring.depends_on:
                ref = VosReference.parse(dep.ref)
                dep_name = ref.path
                if dep.kind == "hard":
                    if dep_name not in enabled_names:
                        failed[mod.name] = f"hard dependency '{dep_name}' is missing or disabled"
                        changed = True
                        break
                    elif dep_name in failed:
                        failed[mod.name] = f"hard dependency '{dep_name}' failed to start"
                        changed = True
                        break
        return changed

    # Cascade until stable (handles A→B→C chains where C is missing)
    while _cascade_failures():
        pass

    # Log failed modules
    for name, reason in failed.items():
        logger.error("module_startup_failed", module=name, reason=reason)

    # Build graph from non-failed enabled modules only
    startable = {name: mod for name, mod in enabled.items() if name not in failed}
    startable_names = set(startable.keys())

    graph: dict[str, set[str]] = {}
    for mod in startable.values():
        deps: set[str] = set()
        for dep in mod.wiring.depends_on:
            ref = VosReference.parse(dep.ref)
            dep_name = ref.path
            if dep_name in startable_names:
                deps.add(dep_name)
            elif dep.kind == "soft":
                logger.warning(
                    "soft_dependency_unavailable",
                    module=mod.name,
                    dependency=dep_name,
                )
            # Hard deps already handled by failure cascade above
        graph[mod.name] = deps

    sorter = TopologicalSorter(graph)
    try:
        sorter.prepare()
    except CycleError as e:
        raise CircularDependencyError(str(e)) from e

    order: list[list[str]] = []
    while sorter.is_active():
        group = sorted(sorter.get_ready())
        order.append(group)
        for name in group:
            sorter.done(name)

    return StartupPlan(order=order, failed=failed)
