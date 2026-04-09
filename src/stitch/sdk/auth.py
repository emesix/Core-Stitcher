"""Auth header resolution."""

from stitch.sdk.config import Profile  # noqa: TC001 — used at runtime


def resolve_auth(profile: Profile, env_token: str | None = None) -> dict[str, str]:
    token = env_token or profile.resolve_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}
