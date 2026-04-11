import httpx
import pytest

from stitch.core.errors import StitchAPIError, StitchTransportError
from stitch.sdk.client import StitchClient
from stitch.sdk.config import Profile


@pytest.fixture
def profile():
    return Profile(server="http://testserver:8000", token="test-token")


async def test_client_query(profile):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/explorer/devices":
            return httpx.Response(
                200,
                json=[{"id": "dev_01", "name": "sw-core-01", "type": "SWITCH"}],
            )
        return httpx.Response(404, json={"detail": "Not found"})

    client = StitchClient(profile, transport=httpx.MockTransport(handler))
    result = await client.query("device", "list")
    assert len(result.items) == 1
    assert result.items[0]["name"] == "sw-core-01"
    await client.close()


async def test_client_query_single(profile):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"id": "dev_01", "name": "sw-core-01", "type": "SWITCH", "ports": []},
        )

    client = StitchClient(profile, transport=httpx.MockTransport(handler))
    result = await client.query("device", "show", resource_id="dev_01")
    assert result.items[0]["name"] == "sw-core-01"
    assert result.total == 1
    await client.close()


async def test_client_command(profile):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"vlan": 42, "status": "complete", "hops": []},
        )

    client = StitchClient(profile, transport=httpx.MockTransport(handler))
    result = await client.command("trace", "run", params={"vlan": 42, "source": "sw-core-01"})
    assert result["status"] == "complete"
    await client.close()


async def test_client_auth_header(profile):
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.headers))
        return httpx.Response(200, json=[])

    client = StitchClient(profile, transport=httpx.MockTransport(handler))
    await client.query("device", "list")
    assert captured.get("authorization") == "Bearer test-token"
    await client.close()


async def test_client_server_error(profile):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            500,
            json={
                "code": "system.unavailable",
                "message": "Internal error",
                "retryable": True,
            },
        )

    client = StitchClient(profile, transport=httpx.MockTransport(handler))
    with pytest.raises(StitchAPIError, match="Internal error"):
        await client.query("device", "list")
    await client.close()


async def test_client_transport_error(profile):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="Bad Gateway")

    client = StitchClient(profile, transport=httpx.MockTransport(handler))
    with pytest.raises(StitchTransportError, match="HTTP 502"):
        await client.query("device", "list")
    await client.close()
