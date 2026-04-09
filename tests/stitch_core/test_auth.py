from datetime import UTC, datetime

from stitch.core.auth import Capability, Session
from stitch.core.commands import CommandSource


def test_capability_values():
    assert Capability.TOPOLOGY_READ == "topology.read"
    assert Capability.ADMIN == "admin"
    assert Capability.PREFLIGHT_RUN == "preflight.run"


def test_session_construction():
    now = datetime.now(UTC)
    sess = Session(
        session_id="sess_001",
        user="emesix",
        capabilities={"topology.read", "preflight.run"},
        client=CommandSource.CLI,
        created_at=now,
    )
    assert sess.session_id == "sess_001"
    assert "topology.read" in sess.capabilities
    assert sess.expires_at is None
    assert sess.scopes is None
