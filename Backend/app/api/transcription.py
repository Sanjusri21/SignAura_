from fastapi import APIRouter, Depends
from app.schemas.transcription import TranscriptionRequest, TranscriptionResponse
from app.services.speech.whisper_service import whisper_service
from app.services.isl.service import get_isl_service
from app.core.database import get_transcriptions_collection
import datetime
import uuid

router = APIRouter(prefix="/transcription", tags=["Speech Transcription"])

@router.post("", response_model=TranscriptionResponse)
async def create_transcription(req: TranscriptionRequest):
    if req.text_override:
        text = req.text_override
        duration = 5.0
        segments = []
    else:
        res = await whisper_service.transcribe(req.audio_path or "", language=req.language or "en")
        text = res.get("text", "")
        duration = res.get("duration", 0.0)
        segments = res.get("segments", [])
        
    isl_service = get_isl_service()
    isl_res = await isl_service.translate_to_gloss(text)
    
    trans_doc = {
        "id": f"trans-{uuid.uuid4().hex[:8]}",
        "text": text,
        "language": req.language or "en",
        "duration": duration,
        "gloss": isl_res.gloss,
        "created_at": datetime.datetime.utcnow().isoformat()
    }
    trans_col = get_transcriptions_collection()
    await trans_col.insert_one(trans_doc)
    
    return TranscriptionResponse(
        text=text,
        language=req.language or "en",
        duration=duration,
        segments=segments,
        gloss_tokens=isl_res.tokens or []
    )
