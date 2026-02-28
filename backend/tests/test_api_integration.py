import pytest
import httpx
from fastapi import status

BASE_URL = "http://localhost:8000"

@pytest.mark.asyncio
async def test_health_check_integration():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["services"]["database"] == "online"

@pytest.mark.asyncio
async def test_stats_endpoint_security():
    # Verify that the stats endpoint is protected and returns 401 without auth
    # follow_redirects=True avoids the 307 Temporary Redirect error
    async with httpx.AsyncClient(base_url=BASE_URL, follow_redirects=True) as client:
        response = await client.get("/api/v1/stats")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_root_endpoint():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        response = await client.get("/")
        assert response.status_code == status.HTTP_200_OK
        assert "Welcome to TraceIQ API" in response.json()["message"]
