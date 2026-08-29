import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter
from app.schemas.chat import ChatRequest, ChatResponse, ChatHistoryResponse, ChatMessageSchema
from app.services.ai.assistant import ai_assistant
from app.core.database import get_chat_sessions_collection, get_chat_messages_collection

router = APIRouter(prefix="/chat", tags=["AI Assistant"])

@router.post("", response_model=ChatResponse)
async def send_chat_message(req: ChatRequest):
    session_id = req.session_id or "default-session"
    now_str = datetime.now().strftime("%I:%M %p")
    
    # Store user message
    user_msg_doc = {
        "id": f"msg-{uuid.uuid4().hex[:8]}",
        "session_id": session_id,
        "sender": "user",
        "text": req.message,
        "timestamp": now_str,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    messages_col = get_chat_messages_collection()
    await messages_col.insert_one(user_msg_doc)
    
    # Generate AI response with ISL gloss
    ai_res = await ai_assistant.generate_response(req.message, dialect=req.dialect or "standard")
    
    ai_msg_doc = {
        "id": ai_res["id"],
        "session_id": session_id,
        "sender": "ai",
        "text": ai_res["text"],
        "timestamp": ai_res["timestamp"],
        "glossSequence": ai_res["glossSequence"],
        "recommendedSigns": ai_res["recommendedSigns"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await messages_col.insert_one(ai_msg_doc)
    
    return ChatResponse(**ai_res)

@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: Optional[str] = "default-session"):
    messages_col = get_chat_messages_collection()
    cursor = messages_col.find({"session_id": session_id})
    msg_list = await cursor.to_list(100)
    
    if not msg_list:
        default_msg = {
            "id": "msg-init-1",
            "sender": "ai",
            "text": "Namaste! I am SignAura AI. Ask me about Indian Sign Language grammar, dialects, emergency signs, or type any phrase to see it signed.",
            "timestamp": "12:00 PM",
            "glossSequence": ["HELLO", "WELCOME", "SIGN_LANGUAGE", "INDIA"],
            "recommendedSigns": ["HELLO", "THANK_YOU", "DOCTOR", "EMERGENCY"]
        }
        return ChatHistoryResponse(
            session_id=session_id,
            messages=[ChatMessageSchema(**default_msg)]
        )
        
    return ChatHistoryResponse(
        session_id=session_id,
        messages=[
            ChatMessageSchema(
                id=m.get("id", str(m.get("_id"))),
                sender=m["sender"],
                text=m["text"],
                timestamp=m.get("timestamp", ""),
                glossSequence=m.get("glossSequence", []),
                recommendedSigns=m.get("recommendedSigns", [])
            )
            for m in msg_list
        ]
    )
