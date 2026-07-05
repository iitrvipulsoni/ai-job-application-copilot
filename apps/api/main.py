from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from database import engine, Base
from config import settings
from routers import auth, resumes, applications, jobs, analysis, profile, versions, feedback

# Automatically compile database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Job Application Copilot API",
    description="Backend API for managing resumes, job descriptions, fitting analysis, and verification logs.",
    version="0.1.0"
)

# Configure CORS
origins = [origin.strip() for origin in settings.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(resumes.router)
app.include_router(applications.router)
app.include_router(jobs.router)
app.include_router(analysis.router)
app.include_router(profile.router)
app.include_router(versions.router)
app.include_router(feedback.router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AI Job Application Copilot API",
        "environment": "development"
    }

@app.get("/")
def root():
    return {
        "message": "Welcome to the AI Job Application Copilot API. Visit /docs for API documentation."
    }
