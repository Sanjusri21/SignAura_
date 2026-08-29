import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import db_manager
from app.utils.logger import logger

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.video import router as video_router
from app.api.transcription import router as transcription_router
from app.api.translation import router as translation_router
from app.api.isl import router as isl_router
from app.api.avatar import router as avatar_router
from app.api.jobs import router as jobs_router
from app.api.chat import router as chat_router
from app.api.history import router as history_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SignAura Backend...")
    await db_manager.connect_to_database()
    logger.info("SignAura Backend ready (Demo Mode: %s)", settings.DEMO_MODE)
    yield
    logger.info("Shutting down SignAura Backend...")
    await db_manager.close_database_connection()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SignAura AI Backend - End-to-End Indian Sign Language & Avatar Engine",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve animations and uploads statically if directory exists
if os.path.exists(settings.ANIMATIONS_DIR):
    app.mount("/animations", StaticFiles(directory=settings.ANIMATIONS_DIR), name="animations")
if os.path.exists(settings.UPLOADS_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOADS_DIR), name="uploads")

# Core Health Check Endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "signaura-backend",
        "version": settings.VERSION,
        "demo_mode": settings.DEMO_MODE,
        "database_connected": db_manager.is_connected,
        "timestamp": os.getenv("CURRENT_TIME", "")
    }

# Include API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(video_router, prefix=settings.API_V1_STR)
app.include_router(transcription_router, prefix=settings.API_V1_STR)
app.include_router(translation_router, prefix=settings.API_V1_STR)
app.include_router(isl_router, prefix=settings.API_V1_STR)
app.include_router(avatar_router, prefix=settings.API_V1_STR)
app.include_router(jobs_router, prefix=settings.API_V1_STR)
app.include_router(chat_router, prefix=settings.API_V1_STR)
app.include_router(history_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
