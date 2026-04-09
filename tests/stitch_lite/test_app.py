import pytest
from httpx import ASGITransport, AsyncClient

from stitch.apps.lite.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_index_page(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "Stitch" in resp.text


@pytest.mark.asyncio
async def test_static_css(client):
    resp = await client.get("/static/style.css")
    assert resp.status_code == 200
    assert "var(--bg)" in resp.text
