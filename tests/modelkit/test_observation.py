from __future__ import annotations

from datetime import UTC, datetime

from stitch.modelkit.enums import ObservationSource
from stitch.modelkit.observation import MergeConflict, Mismatch, Observation


def test_observation_minimal():
    obs = Observation(device="switch-a", field="vlan", value=10, source=ObservationSource.MCP_LIVE)
    assert obs.device == "switch-a"
    assert obs.field == "vlan"
    assert obs.value == 10
    assert obs.source == ObservationSource.MCP_LIVE
    assert obs.port is None
    assert obs.adapter is None
    assert isinstance(obs.timestamp, datetime)


def test_observation_full():
    now = datetime.now(UTC)
    obs = Observation(
        device="switch-a",
        port="eth0",
        field="speed",
        value="1G",
        source=ObservationSource.DECLARED,
        adapter="switchcraft",
        timestamp=now,
    )
    assert obs.port == "eth0"
    assert obs.adapter == "switchcraft"
    assert obs.timestamp == now


def test_observation_default_timestamp():
    obs = Observation(device="d", field="f", value=1, source=ObservationSource.UNKNOWN)
    assert obs.timestamp is not None
    # Should be recent
    delta = datetime.now(UTC) - obs.timestamp.replace(tzinfo=UTC)
    assert abs(delta.total_seconds()) < 10


def test_mismatch_minimal():
    m = Mismatch(
        device="switch-a",
        field="vlan",
        expected=10,
        observed=20,
        source=ObservationSource.MCP_LIVE,
    )
    assert m.device == "switch-a"
    assert m.expected == 10
    assert m.observed == 20
    assert m.severity == "error"
    assert m.message is None
    assert m.port is None


def test_mismatch_full():
    m = Mismatch(
        device="switch-a",
        port="eth0",
        field="speed",
        expected="1G",
        observed="100M",
        source=ObservationSource.MCP_LIVE,
        severity="warning",
        message="Speed negotiation mismatch",
    )
    assert m.port == "eth0"
    assert m.severity == "warning"
    assert m.message == "Speed negotiation mismatch"


def test_merge_conflict_minimal():
    mc = MergeConflict(
        device="switch-a",
        field="vlan",
        sources=["declared", "mcp_live"],
        values=[10, 20],
    )
    assert mc.device == "switch-a"
    assert mc.field == "vlan"
    assert mc.sources == ["declared", "mcp_live"]
    assert mc.values == [10, 20]
    assert mc.resolution is None
    assert mc.port is None


def test_merge_conflict_full():
    mc = MergeConflict(
        device="switch-a",
        port="eth0",
        field="native_vlan",
        sources=["declared", "mcp_live"],
        values=[1, 100],
        resolution="use_declared",
    )
    assert mc.port == "eth0"
    assert mc.resolution == "use_declared"
