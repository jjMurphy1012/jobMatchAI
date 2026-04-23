from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.api import admin, auth, interview_experiences, jobs, preferences, resume, tasks
from app.services.scheduler_service import scheduler_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    if not settings.DEBUG and settings.JWT_SECRET_KEY == "dev-only-change-me":
        raise RuntimeError("JWT_SECRET_KEY must be set in non-debug environments.")
    await init_db()
    if settings.ENABLE_SCHEDULER:
        scheduler_service.start()
    print(f"🚀 {settings.APP_NAME} started!")
    if settings.ENABLE_SCHEDULER:
        print(f"📅 Scheduler running - Daily push at {settings.PUSH_HOUR}:{settings.PUSH_MINUTE:02d} {settings.TIMEZONE}")
    else:
        print("⏸️ Scheduler disabled for this process")
    yield
    # Shutdown
    if settings.ENABLE_SCHEDULER:
        scheduler_service.stop()
    print(f"👋 {settings.APP_NAME} shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered job matching and recommendation system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(resume.router, prefix="/api/resume", tags=["Resume"])
app.include_router(preferences.router, prefix="/api/preferences", tags=["Preferences"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(tasks.router, prefix="/api/daily-tasks", tags=["Daily Tasks"])
app.include_router(interview_experiences.router, prefix="/api/interview-experiences", tags=["Interview Experiences"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.APP_NAME}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/docs",
        "health": "/health"
    }
