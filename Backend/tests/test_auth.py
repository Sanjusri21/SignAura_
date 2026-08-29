import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_auth_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register
        reg_res = await ac.post("/api/auth/register", json={
            "email": "testuser@signaura.org",
            "password": "secretpassword123",
            "full_name": "Test User"
        })
        assert reg_res.status_code == 200
        token = reg_res.json()["access_token"]
        
        # Login
        login_res = await ac.post("/api/auth/login", json={
            "email": "testuser@signaura.org",
            "password": "secretpassword123"
        })
        assert login_res.status_code == 200
        assert "access_token" in login_res.json()
        
        # Me
        me_res = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        assert me_res.json()["email"] == "testuser@signaura.org"
