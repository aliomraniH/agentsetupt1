"""
Main FastAPI server for Back End Health Agent
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from loguru import logger
import sys

from src.core.config import settings
from src.api.routes import health, agents, cached
from src.core.scheduler import get_scheduler


# Configure logging - ensure all logs go to stdout for Replit console
logger.remove()  # Remove default handler

# Add stdout handler with INFO level (captures all our application logs)
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",  # Always INFO to ensure logs are visible in Replit console
    colorize=True,
    backtrace=True,
    diagnose=True
)

# Also add a debug handler if debug mode is enabled
if settings.debug:
    logger.add(
        sys.stderr,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        colorize=False
    )

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Replit Backend for hosting AI Agents and Engines with health monitoring capabilities",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS - Allow all origins for API access
# Note: When allow_credentials=True, browsers require specific origins (not wildcard)
# For public API access from Claude artifacts and other sources, we use wildcard without credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins including Claude artifacts
    allow_credentials=False,  # Must be False when using wildcard origins
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all response headers to the browser
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging visibility in Replit console"""
    logger.info(f"📥 Incoming request: {request.method} {request.url.path}")

    # Process the request
    start_time = datetime.now(timezone.utc)
    response = await call_next(request)
    end_time = datetime.now(timezone.utc)

    # Log response
    duration_ms = (end_time - start_time).total_seconds() * 1000
    logger.info(f"📤 Response: {response.status_code} | {duration_ms:.0f}ms")

    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "detail": str(exc) if settings.debug else None
        }
    )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(agents.router, prefix=settings.api_prefix, tags=["Agents"])
app.include_router(cached.router, prefix=f"{settings.api_prefix}/cached", tags=["Cached Data"])


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "docs": "/docs",
        "health": "/health"
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"API documentation available at /docs")

    # Start background stock cache scheduler
    scheduler = get_scheduler()
    scheduler.start()
    logger.info("✓ Background stock cache scheduler started")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.app_name}")

    # Stop background scheduler
    scheduler = get_scheduler()
    scheduler.stop()
    logger.info("✓ Background scheduler stopped")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.core.server:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
