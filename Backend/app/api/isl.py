from fastapi import APIRouter
from typing import List
from datetime import datetime, timezone
import uuid
from app.schemas.isl import ISLTranslateRequest, ISLTranslateResponse, ISLDictionaryItemSchema
from app.services.isl.service import get_isl_service
from app.services.isl.dictionary import ISL_DICTIONARY
from app.core.database import get_isl_conversions_collection

router = APIRouter(prefix="/isl", tags=["Indian Sign Language"])

@router.post("/translate", response_model=ISLTranslateResponse)
async def translate_text(req: ISLTranslateRequest):
    isl_service = get_isl_service()
    res = await isl_service.translate_to_gloss(req.text, dialect=req.dialect or "standard")
    
    conversions = get_isl_conversions_collection()
    conv_doc = {
        "id": f"conv-{uuid.uuid4().hex[:8]}",
        "text": req.text,
        "dialect": req.dialect or "standard",
        "gloss": res.gloss,
        "animations": res.animations,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await conversions.insert_one(conv_doc)
    
    return res

@router.get("/dictionary", response_model=List[ISLDictionaryItemSchema])
async def get_dictionary():
    return ISL_DICTIONARY
