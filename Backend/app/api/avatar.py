from fastapi import APIRouter
from typing import Dict, Any, List
from app.services.avatar.animator import avatar_animator

router = APIRouter(prefix="/avatar", tags=["SignAvatar 3D"])

@router.get("/poses")
async def get_all_poses() -> Dict[str, Any]:
    return avatar_animator.PRESET_POSES

@router.get("/pose/{gloss}")
async def get_pose_for_gloss(gloss: str) -> Dict[str, Any]:
    return avatar_animator.get_pose_by_gloss(gloss)

@router.get("/animations")
async def get_available_animations() -> List[str]:
    return [
        "hello.glb", "how.glb", "are.glb", "you.glb",
        "thank_you.glb", "welcome.glb", "help.glb", "emergency.glb",
        "doctor.glb", "hospital.glb", "india.glb", "accessible.glb"
    ]
