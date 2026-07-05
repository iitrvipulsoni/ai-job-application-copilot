from pydantic_settings import BaseSettings
from pydantic import ConfigDict
import os

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./copilot.db"
    JWT_SECRET: str = "super_secret_jwt_key_for_development"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    PORT: int = 8000
    UPLOAD_DIR: str = "uploads"
    GEMINI_API_KEY: str = ""
    CORS_ALLOWED_ORIGINS: str = "*"
    ENABLE_DEV_ADMIN_ENDPOINTS: bool = False
    ENABLE_DEV_AI_ENDPOINTS: bool = False

    model_config = ConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
