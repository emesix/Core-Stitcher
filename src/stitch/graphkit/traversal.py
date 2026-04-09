"""Graph traversal — BFS/DFS on topology snapshots."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from vos.modelkit.topology import TopologySnapshot


def bfs(
    snapshot: TopologySnapshot,
    start: str,
    *,
    predicate: Callable[[str], bool] | None = None,
) -> list[str]:
    """BFS from start device, returning reachable device IDs in visit order.

    If predicate is given, only visits neighbors where predicate(device_id) is True.
    """
    if start not in snapshot.devices:
        return []

    visited: set[str] = {start}
    queue: deque[str] = deque([start])
    result: list[str] = [start]

    while queue:
        current = queue.popleft()
        for link in snapshot.links:
            ep_a, ep_b = link.endpoints
            neighbor = None
            if ep_a.device == current and ep_b.device not in visited:
                neighbor = ep_b.device
            elif ep_b.device == current and ep_a.device not in visited:
                neighbor = ep_a.device

            if neighbor is None:
                continue
            if predicate is not None and not predicate(neighbor):
                continue

            visited.add(neighbor)
            queue.append(neighbor)
            result.append(neighbor)

    return result
