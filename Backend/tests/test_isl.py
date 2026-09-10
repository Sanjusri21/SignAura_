import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_isl_translate_demo_case():
    payload = {
        "text": "Hello, how are you?",
        "dialect": "standard"
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/isl/translate", json=payload)
        
    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "Hello, how are you?"
    assert data["gloss"] == ["HELLO", "YOU", "HOW"]
    assert "hello.glb" in data["animations"]
    assert "how.glb" in data["animations"]
    assert data["status"] == "completed"

@pytest.mark.asyncio
async def test_isl_dictionary():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/isl/dictionary")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
