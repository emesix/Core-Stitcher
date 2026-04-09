import os

from stitch.sdk.auth import resolve_auth
from stitch.sdk.config import Profile


def test_resolve_auth_from_profile():
    p = Profile(server="http://localhost:8000", token="tok123")
    headers = resolve_auth(p)
    assert headers["Authorization"] == "Bearer tok123"


def test_resolve_auth_no_token():
    p = Profile(server="http://localhost:8000")
    headers = resolve_auth(p)
    assert "Authorization" not in headers


def test_resolve_auth_env_override(monkeypatch):
    monkeypatch.setenv("STITCH_TOKEN", "env-tok")
    p = Profile(server="http://localhost:8000", token="profile-tok")
    headers = resolve_auth(p, env_token=os.environ.get("STITCH_TOKEN"))
    assert headers["Authorization"] == "Bearer env-tok"
