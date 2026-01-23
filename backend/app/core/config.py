from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Job Matching AI"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/jobmatch"

    # OpenAI
    OPENAI_API_KEY: str = ""

    # LinkedIn
    LINKEDIN_EMAIL: str = ""
    LINKEDIN_PASSWORD: str = ""

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
    PUSH_HOUR: int = 7  # 7 AM EST
    PUSH_MINUTE: int = 0
    TIMEZONE: str = "America/New_York"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
