# app/core/config.py
# Central configuration for the application

from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    # App Info
    APP_NAME: str = "Need Service Connect API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Security - JWT
    SECRET_KEY: str = "zaria-serviceconnect-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database
    DATABASE_URL: str = "sqlite:///./zaria_serviceconnect.db"

    # File Uploads
    UPLOAD_DIR: str = "uploads/documents"
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5 MB

    # Firebase Cloud Messaging
    FIREBASE_SERVICE_ACCOUNT_PATH: str | None = None
    FIREBASE_SERVICE_ACCOUNT_JSON: str | None = None
    FIREBASE_SERVICE_ACCOUNT_BASE64: str | None = None

    # Admin activity emails
    ADMIN_ACTIVITY_EMAIL: str = "abdulahadmood@gmail.com"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "adminzariaserviceconnect@gmail.com"
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str = "adminzariaserviceconnect@gmail.com"
    SMTP_USE_TLS: bool = True
    SMTP_TIMEOUT_SECONDS: int = 10

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_value(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"debug", "dev", "development"}:
                return True
        return value

    class Config:
        env_file = ".env"

# Create a single instance to import everywhere
settings = Settings()
