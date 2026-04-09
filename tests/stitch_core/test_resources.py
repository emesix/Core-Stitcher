import pytest

from stitch.core.resources import Resource, ResourceURI, parse_uri


def test_parse_simple_uri():
    uri = parse_uri("stitch:/device/dev_01HX")
    assert uri.resource_type == "device"
    assert uri.resource_id == "dev_01HX"
    assert uri.sub_resource is None

def test_parse_nested_uri():
    uri = parse_uri("stitch:/run/run_18f2/task/tsk_003F")
    assert uri.resource_type == "run"
    assert uri.resource_id == "run_18f2"
    assert uri.sub_resource == "task"
    assert uri.sub_id == "tsk_003F"

def test_parse_deep_uri():
    uri = parse_uri("stitch:/run/run_18f2/task/tsk_003F/step/stp_007Q")
    assert uri.resource_type == "run"
    assert uri.resource_id == "run_18f2"
    assert uri.sub_resource == "task"
    assert uri.sub_id == "tsk_003F"
    assert uri.extra_path == "step/stp_007Q"

def test_uri_to_string():
    uri = ResourceURI(resource_type="device", resource_id="dev_01HX")
    assert str(uri) == "stitch:/device/dev_01HX"

def test_uri_to_string_nested():
    uri = ResourceURI(
        resource_type="run", resource_id="run_18f2",
        sub_resource="task", sub_id="tsk_003F",
    )
    assert str(uri) == "stitch:/run/run_18f2/task/tsk_003F"

def test_parse_invalid_uri():
    with pytest.raises(ValueError, match="Invalid stitch URI"):
        parse_uri("http://example.com")

def test_resource_model():
    res = Resource(
        uri="stitch:/device/dev_01HX", type="device",
        display_name="sw-core-01", summary="USW-Pro-48-PoE at 192.168.254.2",
    )
    assert res.display_name == "sw-core-01"
    assert res.status is None
