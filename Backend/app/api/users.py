from fastapi import APIRouter, Depends
from app.schemas.auth import UserResponse
from app.api.auth import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: UserResponse = Depends(get_current_user)):
    return current_user
