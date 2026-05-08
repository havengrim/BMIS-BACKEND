from pydantic_settings import BaseSettings
from pydantic import field_validator
from pydantic_settings import SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "BMIS - Barangay Management Information System"
    APP_ENV: str = "development"  # development | staging | production
    DEBUG: bool = False

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_MAX_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_FAIL_OPEN: bool = True
    RATE_LIMIT_EXEMPT_PATHS: List[str] = ["/health", "/docs", "/redoc", "/openapi.json"]

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database (PostgreSQL on AWS RDS)
    DATABASE_URL: str

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # AWS
    AWS_REGION: str = "ap-southeast-1"
    AWS_S3_BUCKET: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # Google OAuth (SSO)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"
    FRONTEND_URL: str = "http://localhost:3000"

    # Redis (rate limiting / session / token blacklist)
    REDIS_URL: str

    # Sentry (error tracking in production)
    SENTRY_DSN: str = ""

    # Celery (background task queue)
    # Defaults to REDIS_URL if not set — override for dedicated broker endpoints
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # DB logging — write app logs to system_logs table
    LOG_TO_DB: bool = True
    LOG_LEVEL_DB: str = "INFO"  # Minimum level written to DB: DEBUG|INFO|WARNING|ERROR|CRITICAL

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_set(cls, v: str) -> str:
        if not v or v == "CHANGE_ME":
            raise ValueError("SECRET_KEY must be set and not default value")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def database_url_must_be_set(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("DATABASE_URL must be set")
        return v

    @field_validator("REDIS_URL")
    @classmethod
    def redis_url_must_be_set(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("REDIS_URL must be set")
        return v

    @field_validator("APP_ENV")
    @classmethod
    def app_env_must_be_valid(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"APP_ENV must be one of: {', '.join(sorted(allowed))}")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
