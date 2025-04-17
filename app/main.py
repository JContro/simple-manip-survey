import logging
import os
import asyncio
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.core.config import settings
from app.routers import users, auth

import time

from app.services.firestore import firestore_service, initialize_firestore_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configure templates
templates = Jinja2Templates(directory="app/templates")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Include routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["authentication"],
)
app.include_router(
    users.router,
    prefix=f"{settings.API_V1_STR}/users",
    tags=["users"],
)

# Root endpoint
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# API info endpoint
@app.get("/api")
async def api_info():
    return {
        "message": "Welcome to the User Management API",
        "docs": f"{settings.API_V1_STR}/docs",
    }

@app.on_event("startup")
async def startup_event():
    """
    Startup event handler to check Firestore connection
    """
    logger.info("Application startup...")
    logger.info(f"Environment variables:")
    logger.info(f"  GCP_PROJECT_ID: {settings.GCP_PROJECT_ID}")
    logger.info(f"  FIRESTORE_COLLECTION: {settings.FIRESTORE_COLLECTION}")
    logger.info(f"  FIRESTORE_EMULATOR_HOST: {os.environ.get('FIRESTORE_EMULATOR_HOST')}")
    logger.info(f"  GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")
    
    await initialize_firestore_service()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)