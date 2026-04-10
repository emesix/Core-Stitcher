from stitch.mcp.schemas import DetailLevel, ErrorCode, ToolResponse


def test_success_response():
    r = ToolResponse.success(result={"count": 5}, summary="Found 5 items.")
    data = r.to_dict()
    assert data["ok"] is True
    assert data["summary"] == "Found 5 items."
    assert data["result"]["count"] == 5
    assert "meta" in data
    assert "generated_at" in data["meta"]


def test_failure_response():
    r = ToolResponse.failure(
        code=ErrorCode.DEVICE_NOT_FOUND,
        message="Device 'xyz' not found in topology",
        summary="Device not found.",
    )
    data = r.to_dict()
    assert data["ok"] is False
    assert data["error"]["code"] == "DEVICE_NOT_FOUND"
    assert data["error"]["message"] == "Device 'xyz' not found in topology"


def test_detail_levels():
    assert DetailLevel.SUMMARY == "summary"
    assert DetailLevel.STANDARD == "standard"
    assert DetailLevel.FULL == "full"


def test_error_codes_exist():
    assert ErrorCode.TOPOLOGY_NOT_FOUND == "TOPOLOGY_NOT_FOUND"
    assert ErrorCode.TOPOLOGY_INVALID == "TOPOLOGY_INVALID"
    assert ErrorCode.DEVICE_NOT_FOUND == "DEVICE_NOT_FOUND"
    assert ErrorCode.DEVICE_AMBIGUOUS == "DEVICE_AMBIGUOUS"
    assert ErrorCode.GATEWAY_UNAVAILABLE == "GATEWAY_UNAVAILABLE"
    assert ErrorCode.GATEWAY_TOOL_ERROR == "GATEWAY_TOOL_ERROR"
    assert ErrorCode.GATEWAY_TIMEOUT == "GATEWAY_TIMEOUT"
    assert ErrorCode.INTERFACE_NOT_FOUND == "INTERFACE_NOT_FOUND"
    assert ErrorCode.INTERFACE_ALREADY_ASSIGNED == "INTERFACE_ALREADY_ASSIGNED"
    assert ErrorCode.APPLY_FAILED == "APPLY_FAILED"
    assert ErrorCode.VERIFICATION_FAILED == "VERIFICATION_FAILED"


def test_response_includes_topology_path():
    r = ToolResponse.success(result={}, summary="ok", topology_path="topologies/lab.json")
    data = r.to_dict()
    assert data["meta"]["topology_path"] == "topologies/lab.json"


def test_response_meta_has_tool_version():
    r = ToolResponse.success(result={}, summary="ok")
    data = r.to_dict()
    assert data["meta"]["tool_version"] == "1.0"
