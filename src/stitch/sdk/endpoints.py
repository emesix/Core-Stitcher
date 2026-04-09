"""Map stitch commands to existing API endpoints."""

from __future__ import annotations

_ENDPOINTS: dict[tuple[str, str], tuple[str, str]] = {
    ("device", "list"): ("GET", "/explorer/devices"),
    ("device", "show"): ("GET", "/explorer/devices/{id}"),
    ("device", "neighbors"): ("GET", "/explorer/devices/{id}/neighbors"),
    ("topology", "show"): ("GET", "/explorer/topology"),
    ("topology", "diagnostics"): ("GET", "/explorer/diagnostics"),
    ("vlan", "show"): ("GET", "/explorer/vlans/{id}"),
    ("preflight", "run"): ("POST", "/verify"),
    ("trace", "run"): ("POST", "/trace"),
    ("impact", "preview"): ("POST", "/impact"),
    ("topology", "diff"): ("POST", "/diff"),
    ("run", "list"): ("GET", "/runs"),
    ("run", "show"): ("GET", "/runs/{id}"),
    ("run", "create"): ("POST", "/runs"),
    ("run", "execute"): ("POST", "/runs/{id}/execute"),
    ("run", "review"): ("POST", "/runs/{id}/review"),
    ("run", "orchestrate"): ("POST", "/runs/{id}/orchestrate"),
    ("system", "health"): ("GET", "/api/v1/health"),
    ("system", "info"): ("GET", "/api/v1/readyz"),
    ("system", "version"): ("GET", "/api/v1/livez"),
    ("module", "list"): ("GET", "/api/v1/modules"),
    ("module", "health"): ("GET", "/health/modules"),
}


def resolve_endpoint(
    resource_type: str, verb: str, resource_id: str | None = None
) -> tuple[str, str]:
    key = (resource_type, verb)
    if key not in _ENDPOINTS:
        msg = f"No endpoint for {resource_type}.{verb}"
        raise KeyError(msg)
    method, template = _ENDPOINTS[key]
    path = template.replace("{id}", resource_id or "")
    return method, path
