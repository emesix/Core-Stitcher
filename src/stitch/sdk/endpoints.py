"""Map stitch commands to existing API endpoints."""

from __future__ import annotations

_ENDPOINTS: dict[tuple[str, str], tuple[str, str]] = {
    # Explorer (topology browser)
    ("device", "list"): ("GET", "/api/v1/explorer/devices"),
    ("device", "show"): ("GET", "/api/v1/explorer/devices/{id}"),
    ("device", "neighbors"): ("GET", "/api/v1/explorer/devices/{id}/neighbors"),
    ("topology", "show"): ("GET", "/api/v1/explorer/topology"),
    ("topology", "diagnostics"): ("GET", "/api/v1/explorer/diagnostics"),
    ("vlan", "show"): ("GET", "/api/v1/explorer/vlans/{id}"),
    # Preflight (verification engine)
    ("preflight", "run"): ("POST", "/api/v1/verify"),
    ("trace", "run"): ("POST", "/api/v1/trace"),
    ("impact", "preview"): ("POST", "/api/v1/impact"),
    ("topology", "diff"): ("POST", "/api/v1/diff"),
    # Runs (project stitcher)
    ("run", "list"): ("GET", "/api/v1/runs"),
    ("run", "show"): ("GET", "/api/v1/runs/{id}"),
    ("run", "create"): ("POST", "/api/v1/runs"),
    ("run", "execute"): ("POST", "/api/v1/runs/{id}/execute"),
    ("run", "review"): ("POST", "/api/v1/runs/{id}/review"),
    ("run", "orchestrate"): ("POST", "/api/v1/runs/{id}/orchestrate"),
    # OPNsense
    ("opnsense", "summary"): ("GET", "/api/v1/opnsense/summary"),
    ("opnsense", "interfaces"): ("GET", "/api/v1/opnsense/interfaces"),
    ("opnsense", "routes"): ("GET", "/api/v1/opnsense/routes"),
    ("opnsense", "aliases"): ("GET", "/api/v1/opnsense/aliases"),
    ("opnsense", "nat"): ("GET", "/api/v1/opnsense/nat"),
    ("opnsense", "vlans"): ("GET", "/api/v1/opnsense/vlans"),
    ("opnsense", "bridges"): ("GET", "/api/v1/opnsense/bridges"),
    # System
    ("system", "health"): ("GET", "/api/v1/health"),
    ("system", "info"): ("GET", "/api/v1/readyz"),
    ("system", "version"): ("GET", "/api/v1/livez"),
    ("module", "list"): ("GET", "/api/v1/modules"),
    ("module", "health"): ("GET", "/api/v1/health/modules"),
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
