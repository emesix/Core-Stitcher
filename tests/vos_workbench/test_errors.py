def test_workbench_error_creation():
    from stitch_workbench.errors import WorkbenchError

    err = WorkbenchError(
        source_module=None,
        severity="error",
        category="config",
        retryable=False,
        message="Module 'foo' has invalid config",
        user_summary="Config error in foo",
    )
    assert err.error_id is not None
    assert err.detail_truncated is False
    assert err.artifact_ref is None


def test_workbench_error_with_details():
    from stitch_workbench.errors import WorkbenchError

    err = WorkbenchError(
        source_module="2db742d5-5f23-4ce0-9c83-7d4dbf18e2c3",
        severity="warning",
        category="dependency",
        retryable=True,
        message="Soft dependency 'memory-main' unavailable",
        user_summary="Memory module down",
        details={"dependency": "memory-main", "reason": "timeout"},
    )
    assert err.retryable is True
    assert err.details["dependency"] == "memory-main"
