from pydantic import BaseModel, Field
from typing import Optional, List

class ChatRequest(BaseModel):
    message: str = Field(..., json_schema_extra={"example": "How do I sign emergency help?"})
    session_id: Optional[str] = "default-session"
    dialect: Optional[str] = "standard"

class ChatMessageSchema(BaseModel):
    id: str
    sender: str # "user" | "ai"
    text: str
    timestamp: str
    glossSequence: Optional[List[str]] = []
    recommendedSigns: Optional[List[str]] = []

class ChatResponse(BaseModel):
    id: str
    text: str
    timestamp: str
    glossSequence: List[str] = []
    recommendedSigns: List[str] = []
    sender: str = "ai"

class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatMessageSchema]
