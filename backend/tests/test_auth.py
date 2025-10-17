import pytest
from app.main import app
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "Hybrid Passwordless Authentication System" in response.json()["message"]


@pytest.mark.asyncio
async def test_openid_configuration():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/.well-known/openid-configuration")
        if response.status_code != 200:
            pytest.fail(
                f"Expected status code 200, got {response.status_code}: {response.text}"
            )
        json_data = response.json()
        assert isinstance(json_data, dict), "Response is not a JSON object"
        assert "issuer" in json_data, "'issuer' not found in response"
