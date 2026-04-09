from stitch.core.lifecycle import LifecycleState, is_terminal, valid_transition


def test_lifecycle_states():
    assert LifecycleState.PENDING == "pending"
    assert LifecycleState.QUEUED == "queued"
    assert LifecycleState.RUNNING == "running"
    assert LifecycleState.SUCCEEDED == "succeeded"

def test_terminal_states():
    assert is_terminal(LifecycleState.SUCCEEDED) is True
    assert is_terminal(LifecycleState.FAILED) is True
    assert is_terminal(LifecycleState.CANCELLED) is True
    assert is_terminal(LifecycleState.TIMED_OUT) is True
    assert is_terminal(LifecycleState.RUNNING) is False
    assert is_terminal(LifecycleState.PENDING) is False

def test_valid_transitions():
    assert valid_transition(LifecycleState.PENDING, LifecycleState.QUEUED) is True
    assert valid_transition(LifecycleState.PENDING, LifecycleState.CANCELLED) is True
    assert valid_transition(LifecycleState.PENDING, LifecycleState.FAILED) is True
    assert valid_transition(LifecycleState.QUEUED, LifecycleState.RUNNING) is True
    assert valid_transition(LifecycleState.RUNNING, LifecycleState.SUCCEEDED) is True
    assert valid_transition(LifecycleState.RUNNING, LifecycleState.CANCELLED) is True
    assert valid_transition(LifecycleState.RUNNING, LifecycleState.TIMED_OUT) is True

def test_invalid_transitions():
    assert valid_transition(LifecycleState.SUCCEEDED, LifecycleState.RUNNING) is False
    assert valid_transition(LifecycleState.FAILED, LifecycleState.PENDING) is False
    assert valid_transition(LifecycleState.PENDING, LifecycleState.SUCCEEDED) is False
