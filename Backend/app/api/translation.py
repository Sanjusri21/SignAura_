from fastapi import APIRouter
from app.schemas.isl import ISLTranslateRequest, ISLTranslateResponse
from app.services.isl.service import get_isl_service

router = APIRouter(prefix="/translation", tags=["Translation"])

@router.post("", response_model=ISLTranslateResponse)
async def translate(req: ISLTranslateRequest):
    isl_service = get_isl_service()
    return await isl_service.translate_to_gloss(req.text, dialect=req.dialect or "standard")
