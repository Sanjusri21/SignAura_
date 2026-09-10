from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel
import httpx

from app.services.avatar.animator import avatar_animator


router = APIRouter(
    prefix="/avatar",
    tags=["SignAvatar 3D"]
)


class SignAvatarRequest(BaseModel):
    sentence: str


@router.get("/poses")
async def get_all_poses() -> Dict[str, Any]:
    return avatar_animator.PRESET_POSES


@router.get("/pose/{gloss}")
async def get_pose_for_gloss(gloss: str) -> Dict[str, Any]:
    return avatar_animator.get_pose_by_gloss(gloss)


@router.get("/animations")
async def get_available_animations() -> List[str]:
    return [
        "hello.glb",
        "how.glb",
        "are.glb",
        "you.glb",
        "thank_you.glb",
        "welcome.glb",
        "help.glb",
        "emergency.glb",
        "doctor.glb",
        "hospital.glb",
        "india.glb",
        "accessible.glb"
    ]


@router.post("/signavatar")
async def signavatar(request: SignAvatarRequest):

    sentence = request.sentence.strip()

    if not sentence:
        raise HTTPException(
            status_code=400,
            detail="Sentence cannot be empty"
        )

    print()
    print("=" * 60)
    print("SIGNAVATAR REQUEST")
    print("=" * 60)
    print("Sentence:", sentence)

    try:

        async with httpx.AsyncClient() as client:

            response = await client.post(
                "http://127.0.0.1:8001/generate",
                json={
                    "sentence": sentence
                },
                timeout=300.0
            )

    except httpx.RequestError as e:

        raise HTTPException(
            status_code=503,
            detail=f"SignAvatar service unavailable: {str(e)}"
        )

    if response.status_code != 200:

        raise HTTPException(
            status_code=500,
            detail=response.text
        )

    result = response.json()

    return {
        "status": "success",
        "sentence": sentence,
        "gif": result.get("gif"),
        "motion": result.get("motion") or result.get("npy"),
        "npy": result.get("npy"),
        "segments": result.get("segments", []),
        "total_frames": result.get("total_frames"),
        "fps": result.get("fps", 20),
        "vertices": result.get("vertices", 10475),
        "components": result.get("components", 3),
        "animation_url":
            "http://127.0.0.1:8001" + result.get("gif", "")
    }