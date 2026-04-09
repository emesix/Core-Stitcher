from stitch.core.errors import FieldError, StitchError, TransportError


def test_stitch_error_construction():
    err = StitchError(code="device.not_found", message="Device not found", retryable=False)
    assert err.code == "device.not_found"
    assert err.retryable is False
    assert err.detail is None
    assert err.field_errors is None

def test_stitch_error_with_field_errors():
    err = StitchError(
        code="command.invalid_params", message="Invalid parameters", retryable=False,
        field_errors=[FieldError(field="vlan_id", code="required", message="VLAN ID is required")],
    )
    assert len(err.field_errors) == 1
    assert err.field_errors[0].field == "vlan_id"

def test_transport_error():
    err = TransportError(kind="timeout", message="Request timed out after 30s", retryable=True)
    assert err.kind == "timeout"
    assert err.retryable is True
