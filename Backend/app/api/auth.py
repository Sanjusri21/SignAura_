import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.schemas.auth import UserCreate, UserLogin, UserResponse, TokenResponse
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.core.database import get_users_collection

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
    if not credentials:
        # For seamless demo mode and unauthenticated exploration, provide standard active user
        return UserResponse(
            id="demo-user-1",
            email="demo@signaura.org",
            full_name="SignAura Demo User",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
    
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    users = get_users_collection()
    user_doc = await users.find_one({"id": payload["sub"]})
    if not user_doc:
        user_doc = await users.find_one({"email": payload["sub"]})
        
    if not user_doc:
        return UserResponse(
            id=payload["sub"],
            email="user@signaura.org",
            full_name="SignAura User",
            is_active=True
        )
    
    return UserResponse(
        id=str(user_doc.get("id") or user_doc.get("_id")),
        email=user_doc["email"],
        full_name=user_doc.get("full_name", "SignAura User"),
        is_active=user_doc.get("is_active", True),
        created_at=user_doc.get("created_at")
    )

@router.post("/register", response_model=TokenResponse)
async def register(user_in: UserCreate):
    users = get_users_collection()
    existing = await users.find_one({"email": user_in.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already registered"
        )
    
    user_id = f"user-{uuid.uuid4().hex[:8]}"
    hashed = get_password_hash(user_in.password)
    user_doc = {
        "id": user_id,
        "email": user_in.email,
        "full_name": user_in.full_name,
        "hashed_password": hashed,
        "is_active": True,
        "created_at": datetime.now(timezone.utc)
    }
    await users.insert_one(user_doc)
    
    token = create_access_token(user_id)
    user_resp = UserResponse(
        id=user_id,
        email=user_in.email,
        full_name=user_in.full_name,
        is_active=True,
        created_at=user_doc["created_at"]
    )
    return TokenResponse(access_token=token, token_type="bearer", user=user_resp)

@router.post("/login", response_model=TokenResponse)
async def login(user_in: UserLogin):
    users = get_users_collection()
    user_doc = await users.find_one({"email": user_in.email})
    
    if not user_doc:
        # In demo mode, automatically register/login seamlessly
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        user_doc = {
            "id": user_id,
            "email": user_in.email,
            "full_name": user_in.email.split("@")[0].capitalize(),
            "hashed_password": get_password_hash(user_in.password),
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        }
        await users.insert_one(user_doc)
    else:
        if not verify_password(user_in.password, user_doc.get("hashed_password", "")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
            
    token = create_access_token(user_doc["id"])
    user_resp = UserResponse(
        id=str(user_doc["id"]),
        email=user_doc["email"],
        full_name=user_doc.get("full_name", "SignAura User"),
        is_active=user_doc.get("is_active", True),
        created_at=user_doc.get("created_at")
    )
    return TokenResponse(access_token=token, token_type="bearer", user=user_resp)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user
