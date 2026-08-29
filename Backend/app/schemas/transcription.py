from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.isl import GlossTokenSchema


class TranscriptionRequest(BaseModel):
    audio_path: Optional[str] = None
    language: Optional[str] = None
    # Only for explicit tests/demo. Real video processing must use audio.
    text_override: Optional[str] = None


class TranscriptionSegment(BaseModel):
    id: int
    seek: int = 0
    start: float
    end: float
    text: str
    tokens: Optional[List[int]] = None
    temperature: Optional[float] = 0.0
    avg_logprob: Optional[float] = 0.0
    compression_ratio: Optional[float] = 0.0
    no_speech_prob: Optional[float] = 0.0


class TranscriptionResponse(BaseModel):
    text: str
    language: str = "en"
    duration: float = 0.0
    segments: List[TranscriptionSegment] = Field(default_factory=list)
    gloss_tokens: List[GlossTokenSchema] = Field(default_factory=list)
