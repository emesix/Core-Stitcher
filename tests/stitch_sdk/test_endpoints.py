import pytest

from stitch.sdk.endpoints import resolve_endpoint


def test_device_list():
    method, path = resolve_endpoint("device", "list")
    assert method == "GET" and path == "/explorer/devices"


def test_device_show():
    method, path = resolve_endpoint("device", "show", resource_id="dev_01HX")
    assert method == "GET" and path == "/explorer/devices/dev_01HX"


def test_device_neighbors():
    _, path = resolve_endpoint("device", "neighbors", resource_id="dev_01HX")
    assert path == "/explorer/devices/dev_01HX/neighbors"


def test_topology_show():
    assert resolve_endpoint("topology", "show") == ("GET", "/explorer/topology")


def test_diagnostics():
    assert resolve_endpoint("topology", "diagnostics") == ("GET", "/explorer/diagnostics")


def test_vlan_show():
    _, path = resolve_endpoint("vlan", "show", resource_id="42")
    assert path == "/explorer/vlans/42"


def test_preflight_run():
    assert resolve_endpoint("preflight", "run") == ("POST", "/verify")


def test_trace_run():
    assert resolve_endpoint("trace", "run") == ("POST", "/trace")


def test_impact_preview():
    assert resolve_endpoint("impact", "preview") == ("POST", "/impact")


def test_run_list():
    assert resolve_endpoint("run", "list") == ("GET", "/runs")


def test_run_show():
    _, path = resolve_endpoint("run", "show", resource_id="run_18f2")
    assert path == "/runs/run_18f2"


def test_run_execute():
    method, path = resolve_endpoint("run", "execute", resource_id="run_18f2")
    assert method == "POST" and path == "/runs/run_18f2/execute"


def test_system_health():
    assert resolve_endpoint("system", "health") == ("GET", "/api/v1/health")


def test_unknown_endpoint():
    with pytest.raises(KeyError, match="No endpoint for bogus.nope"):
        resolve_endpoint("bogus", "nope")
