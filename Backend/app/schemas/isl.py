from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class GlossTokenSchema(BaseModel):
    id: str
    word: str
    gloss: str
    startTime: float
    endTime: float
    confidence: float
    category: Optional[str] = None
    grammarTag: Optional[str] = None
    animationFile: Optional[str] = None

class ISLTranslateRequest(BaseModel):
    text: str = Field(..., json_schema_extra={"example": "Hello, how are you?"})
    dialect: Optional[str] = Field(default="standard", json_schema_extra={"example": "standard"}) # standard, north, south
    grammar_reorder: Optional[bool] = True

class ISLTranslateResponse(BaseModel):
    text: str
    gloss: List[str]
    animations: List[str]
    status: str = "completed"
    tokens: Optional[List[GlossTokenSchema]] = None
    dialect: Optional[str] = "standard"
    disclaimer: Optional[str] = "Animations are demonstrative 3D representations and not certified authentic ISL signs."

class ISLDictionaryItemSchema(BaseModel):
    id: str
    word: str
    gloss: str
    category: str
    definition: str
    exampleSentence: str
    difficulty: str
    animationFile: Optional[str] = None
