"""
Health check endpoints for the backend service
"""

from fastapi import APIRouter
from datetime import datetime, timezone
import platform
import sys

from src.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Quick health check endpoint.
    Returns basic health status of the backend service.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": settings.app_name,
        "version": settings.app_version
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with system information.
    Returns comprehensive health status including system metrics.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": {
            "name": settings.app_name,
            "version": settings.app_version,
            "debug": settings.debug
        },
        "system": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor() or "unknown"
        },
        "configuration": {
            "api_prefix": settings.api_prefix,
            "health_check_timeout": settings.health_check_timeout,
            "health_check_interval": settings.health_check_interval
        }
    }


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes-style readiness probe.
    Returns whether the service is ready to accept traffic.
    """
    # Add actual readiness checks here (database connections, etc.)
    return {
        "ready": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/live")
async def liveness_check():
    """
    Kubernetes-style liveness probe.
    Returns whether the service is alive and running.
    """
    return {
        "alive": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
