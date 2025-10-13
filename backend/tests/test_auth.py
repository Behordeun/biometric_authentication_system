import pytest
from httpx import AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "Hybrid Authentication System" in response.json()["message"]


@pytest.mark.asyncio
async def test_openid_configuration():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/.well-known/openid-configuration")
        assert response.status_code == 200
        assert "issuer" in response.json()
