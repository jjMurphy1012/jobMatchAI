from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.api import resume, preferences, jobs, tasks
from app.services.scheduler_service import scheduler_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    await init_db()
    scheduler_service.start()
    print(f"🚀 {settings.APP_NAME} started!")
    print(f"📅 Scheduler running - Daily push at {settings.PUSH_HOUR}:{settings.PUSH_MINUTE:02d} {settings.TIMEZONE}")
    yield
    # Shutdown
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
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        # Allow Railway frontend domains (will be added in production)
        "*"  # For Railway deployment - consider restricting in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(resume.router, prefix="/api/resume", tags=["Resume"])
app.include_router(preferences.router, prefix="/api/preferences", tags=["Preferences"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(tasks.router, prefix="/api/daily-tasks", tags=["Daily Tasks"])


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
