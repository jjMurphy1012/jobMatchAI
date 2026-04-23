from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

    # App
    APP_NAME: str = "Job Matching AI"
    DEBUG: bool = False
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/jobmatch"

    # Auth
    JWT_SECRET_KEY: str = "dev-only-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    AUTH_COOKIE_DOMAIN: Optional[str] = None
    AUTH_COOKIE_SECURE: bool = False
    AUTH_COOKIE_SAMESITE: str = "lax"
    ACCESS_COOKIE_NAME: str = "jobmatch_access_token"
    REFRESH_COOKIE_NAME: str = "jobmatch_refresh_token"
    OAUTH_STATE_COOKIE_NAME: str = "jobmatch_oauth_state"
    AUTH_RATE_LIMIT_MAX_REQUESTS: int = 10
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:5173/api/auth/google/callback"
    ADMIN_EMAILS: str = ""

    # Storage
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_DIR: str = "uploads"
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_RESUME_BUCKET: str = "resumes"
    SUPABASE_SIGNED_URL_TTL_SECONDS: int = 3600

    # OpenAI
    OPENAI_API_KEY: str = ""

    # LinkedIn (legacy - no longer used)
    LINKEDIN_EMAIL: str = ""
    LINKEDIN_PASSWORD: str = ""

    # RapidAPI (for JSearch job search API)
    RAPIDAPI_KEY: Optional[str] = None

    # Email (optional for now)
    SENDGRID_API_KEY: Optional[str] = None

    # Matching Configuration
    MATCH_THRESHOLD: int = 70
    MIN_THRESHOLD: int = 30
    THRESHOLD_STEP: int = 5
    TARGET_JOBS: int = 10

    # Data Retention
    DATA_RETENTION_DAYS: int = 7

    # Scheduler
    ENABLE_SCHEDULER: bool = False
    PUSH_HOUR: int = 7  # 7 AM EST
    PUSH_MINUTE: int = 0
    TIMEZONE: str = "America/New_York"

    @property
    def cors_origins(self) -> list[str]:
        return _split_csv(self.BACKEND_CORS_ORIGINS)

    @property
    def admin_emails(self) -> set[str]:
        return {email.lower() for email in _split_csv(self.ADMIN_EMAILS)}


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]

settings = Settings()
