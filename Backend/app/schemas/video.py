from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.isl import GlossTokenSchema


class VideoProcessUrlRequest(BaseModel):
    url: str = Field(
        ...,
        min_length=10,
        json_schema_extra={
            "example": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        },
    )
    title: Optional[str] = "Web Video Processing"
    dialect: Optional[str] = "standard"


class VideoJobResponse(BaseModel):
    job_id: str
    status: str  # queued, processing, completed, failed
    title: str
    video_url: Optional[str] = None
    original_file_name: Optional[str] = None
    created_at: str
    progress: int = 0
    duration: float = 0.0
    accuracy: float = 0.0
    language: str = "en"
    dialect: str = "standard"
    transcript: str = ""
    gloss_tokens: List[GlossTokenSchema] = Field(default_factory=list)
    error: Optional[str] = None
