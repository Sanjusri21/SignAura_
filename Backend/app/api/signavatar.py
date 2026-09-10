"""
SignAvatar 3D ISL Motion Endpoints.
Exposes BridgeConn ISL 3D avatar animations and metadata to SignAura clients.
"""

from fastapi import APIRouter, HTTPException, Response
from typing import Dict, Any, List
from pydantic import BaseModel, Field, field_validator

from app.services.signavatar_client import signavatar_client
from app.services.isl_animation_service import isl_animation_service
from app.services.animation_sequencer import animation_sequencer

router = APIRouter(
    prefix="/signavatar",
    tags=["SignAvatar ISL Motions"]
)


class GlossSequenceRequest(BaseModel):
    glosses: List[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of ISL gloss names to resolve"
    )

    @field_validator("glosses")
    @classmethod
    def validate_glosses(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("Gloss list cannot be empty")
        cleaned = []
        for item in v:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("Each gloss must be a non-empty string")
            cleaned.append(item.strip())
        if len(cleaned) > 50:
            raise ValueError("Maximum 50 glosses permitted per batch request")
        return cleaned


@router.get("/motions")
async def list_available_motions() -> Dict[str, Any]:
    """List all available BridgeConn ISL 3D animations."""
    motions = await signavatar_client.get_available_motions()
    return {
        "motions": motions,
        "count": len(motions)
    }


@router.get("/search/{query}")
async def search_motions(query: str) -> Dict[str, Any]:
    """Search available BridgeConn ISL animations by keyword."""
    matches = await signavatar_client.search_motion(query)
    return {
        "query": query,
        "matches": matches,
        "count": len(matches)
    }


@router.get("/motion/{gloss}")
async def get_motion_for_gloss(gloss: str) -> Dict[str, Any]:
    """
    Resolves a requested gloss to its 3D ISL animation metadata and streaming URL.
    Returns available=true with metadata and animation_url, or available=false if no matching sign exists.
    """
    result = await signavatar_client.resolve_gloss_animation(gloss)
    return result


@router.post("/resolve")
async def resolve_gloss_sequence_endpoint(req: GlossSequenceRequest) -> Dict[str, Any]:
    """
    Resolves a sequence of ISL glosses into individual 3D SMPL-X animations and metadata.
    Preserves input order and flags available vs unavailable glosses without omitting any.
    """
    result = await isl_animation_service.resolve_gloss_sequence(req.glosses)
    return result


@router.post("/sequence")
async def create_motion_sequence_endpoint(req: GlossSequenceRequest) -> Dict[str, Any]:
    """
    Combines multiple SMPL-X ISL animations into a single continuous 3D motion.
    Resamples animations to uniform 30 FPS and blends transitions.
    If any gloss is unavailable, returns structured unavailable response with no combined animation generated.
    """
    result = await animation_sequencer.sequence_glosses(req.glosses)
    if "vertices" in result:
        res_copy = dict(result)
        res_copy.pop("vertices", None)
        return res_copy
    return result


@router.get("/sequence/{sequence_id}")
async def get_sequence_motion_stream(sequence_id: str):
    """
    Serves a generated combined SMPL-X motion sequence as a raw binary Float32 vertex buffer.
    Prevents path traversal and validates dimensions (frames x 10475 x 3).
    """
    try:
        binary_data, headers = animation_sequencer.get_sequence_binary(sequence_id)
        return Response(
            content=binary_data,
            media_type="application/octet-stream",
            headers=headers
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except FileNotFoundError as fe:
        raise HTTPException(status_code=404, detail=str(fe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving sequence motion: {str(e)}")


@router.get("/sequence/{sequence_id}/metadata")
async def get_sequence_metadata_endpoint(sequence_id: str) -> Dict[str, Any]:
    """
    Returns JSON metadata for a generated combined motion sequence.
    """
    try:
        return animation_sequencer.get_sequence_metadata(sequence_id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except FileNotFoundError as fe:
        raise HTTPException(status_code=404, detail=str(fe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading sequence metadata: {str(e)}")



