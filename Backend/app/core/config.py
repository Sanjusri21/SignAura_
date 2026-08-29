import os
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "SignAura Backend"
    API_V1_STR: str = "/api"
    VERSION: str = "1.0.0"
    
    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017/signaura"
    DATABASE_NAME: str = "signaura"
    
    # Security
    JWT_SECRET: str = "signaura_super_secret_jwt_key_change_in_production_2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # Redis & Celery
    REDIS_URI: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # AI & Speech Models
    WHISPER_MODEL: str = "base"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    
    # Demo & Operation Modes
    DEMO_MODE: bool = False
    ENABLE_CELERY: bool = False
    APP_ENV: str = "development"
    
    # CORS
    ALLOWED_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    @field_validator("ALLOWED_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v
    
    # Storage Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    UPLOADS_DIR: str = os.path.join(BASE_DIR, "uploads")
    ANIMATIONS_DIR: str = os.path.join(BASE_DIR, "animations")
    MODELS_DIR: str = os.path.join(BASE_DIR, "models")

settings = Settings()

# Ensure required directories exist
os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
os.makedirs(settings.ANIMATIONS_DIR, exist_ok=True)
os.makedirs(settings.MODELS_DIR, exist_ok=True)
