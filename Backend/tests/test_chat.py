import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_chat_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        chat_res = await ac.post("/api/chat", json={
            "message": "Hello, how are you?",
            "session_id": "test-session-1"
        })
        assert chat_res.status_code == 200
        data = chat_res.json()
        assert "text" in data
        assert "glossSequence" in data
        assert data["sender"] == "ai"
        
        hist_res = await ac.get("/api/chat/history?session_id=test-session-1")
        assert hist_res.status_code == 200
        hist_data = hist_res.json()
        assert len(hist_data["messages"]) >= 2
