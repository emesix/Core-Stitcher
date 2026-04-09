from stitch.core.commands import (
    Command,
    CommandSource,
    ExecutionMode,
    InteractionClass,
    RiskLevel,
)


def test_command_construction():
    cmd = Command(
        action="preflight.run",
        target="stitch:/topology/current",
        params={"scope": "site-rdam"},
        source=CommandSource.CLI,
        correlation_id="abc123",
    )
    assert cmd.action == "preflight.run"
    assert cmd.idempotency_key is None


def test_command_source_values():
    assert CommandSource.CLI == "cli"
    assert CommandSource.TUI == "tui"
    assert CommandSource.SCRIPT == "script"


def test_execution_mode():
    assert ExecutionMode.SYNC == "sync"
    assert ExecutionMode.ASYNC == "async"


def test_risk_level():
    assert RiskLevel.LOW == "low"
    assert RiskLevel.HIGH == "high"


def test_interaction_class():
    assert InteractionClass.NONE == "none"
    assert InteractionClass.CONFIRM == "confirm"
