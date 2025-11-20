"""
Health Monitor Agent - Monitors health of deployment environments
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum
import httpx
import asyncio
from loguru import logger

from src.agents.base import BaseAgent
from src.core.config import settings


class HealthStatus(str, Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceType(str, Enum):
    """Types of services that can be monitored"""
    BACKEND = "backend"
    FRONTEND = "frontend"
    DATABASE = "database"
    EXTERNAL = "external"


class HealthMonitorAgent(BaseAgent):
    """
    Agent for monitoring health of deployment environments.

    Currently monitors:
    - Backend service health (this service)

    Future capabilities:
    - Frontend health checks
    - Third-party service monitoring
    - Database connectivity
    - Custom endpoint monitoring
    """

    def __init__(self):
        super().__init__()
        self._targets: List[Dict[str, Any]] = []
        self._history: List[Dict[str, Any]] = []
        self._max_history = 100  # Keep last 100 checks

        # Initialize with self-check target
        self._add_default_targets()

    @property
    def name(self) -> str:
        return "health-monitor"

    @property
    def description(self) -> str:
        return "Monitors health of deployment environments and services"

    def _add_default_targets(self):
        """Add default monitoring targets"""
        # Self-check (this backend)
        self._targets.append({
            "id": "backend-self",
            "name": "Backend Service",
            "type": ServiceType.BACKEND,
            "url": f"http://localhost:{settings.port}/health",
            "timeout": settings.health_check_timeout,
            "enabled": True
        })

    def add_target(
        self,
        target_id: str,
        name: str,
        url: str,
        service_type: ServiceType = ServiceType.EXTERNAL,
        timeout: int = 30,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Add a new monitoring target.

        Args:
            target_id: Unique identifier for the target
            name: Human-readable name
            url: Health check URL
            service_type: Type of service
            timeout: Request timeout in seconds
            enabled: Whether to include in checks

        Returns:
            The created target configuration
        """
        # Check for duplicate ID
        if any(t["id"] == target_id for t in self._targets):
            raise ValueError(f"Target with id '{target_id}' already exists")

        target = {
            "id": target_id,
            "name": name,
            "type": service_type,
            "url": url,
            "timeout": timeout,
            "enabled": enabled
        }

        self._targets.append(target)
        logger.info(f"[{self.name}] Added target: {name} ({url})")
        return target

    def remove_target(self, target_id: str) -> bool:
        """Remove a monitoring target by ID"""
        for i, target in enumerate(self._targets):
            if target["id"] == target_id:
                # Don't allow removing the self-check
                if target_id == "backend-self":
                    raise ValueError("Cannot remove the default backend self-check")
                del self._targets[i]
                logger.info(f"[{self.name}] Removed target: {target_id}")
                return True
        return False

    def get_targets(self) -> List[Dict[str, Any]]:
        """Get all monitoring targets"""
        return self._targets.copy()

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get health check history"""
        return self._history[-limit:]

    async def _check_target(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check health of a single target.

        Args:
            target: Target configuration

        Returns:
            Health check result
        """
        start_time = datetime.now(timezone.utc)
        result = {
            "target_id": target["id"],
            "target_name": target["name"],
            "target_type": target["type"],
            "url": target["url"],
            "checked_at": start_time.isoformat()
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    target["url"],
                    timeout=target["timeout"]
                )

                end_time = datetime.now(timezone.utc)
                response_time = (end_time - start_time).total_seconds() * 1000  # ms

                result.update({
                    "status": HealthStatus.HEALTHY if response.status_code == 200 else HealthStatus.DEGRADED,
                    "status_code": response.status_code,
                    "response_time_ms": round(response_time, 2),
                    "response_body": response.json() if response.headers.get("content-type", "").startswith("application/json") else None
                })

                # Check for degraded status based on response time
                if response_time > 5000:  # > 5 seconds is degraded
                    result["status"] = HealthStatus.DEGRADED
                    result["warning"] = "High response time"

        except httpx.TimeoutException:
            result.update({
                "status": HealthStatus.UNHEALTHY,
                "error": "Request timed out",
                "response_time_ms": target["timeout"] * 1000
            })
        except httpx.ConnectError as e:
            result.update({
                "status": HealthStatus.UNHEALTHY,
                "error": f"Connection failed: {str(e)}",
                "response_time_ms": None
            })
        except Exception as e:
            result.update({
                "status": HealthStatus.UNKNOWN,
                "error": f"Unexpected error: {str(e)}",
                "response_time_ms": None
            })

        return result

    async def run(self, target_ids: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """
        Run health checks on all enabled targets or specific targets.

        Args:
            target_ids: Optional list of specific target IDs to check.
                       If None, checks all enabled targets.

        Returns:
            Dict containing health check results for all targets
        """
        # Determine which targets to check
        if target_ids:
            targets_to_check = [t for t in self._targets if t["id"] in target_ids]
            if not targets_to_check:
                return {
                    "overall_status": HealthStatus.UNKNOWN,
                    "message": "No matching targets found",
                    "targets_checked": 0,
                    "results": []
                }
        else:
            targets_to_check = [t for t in self._targets if t.get("enabled", True)]

        if not targets_to_check:
            return {
                "overall_status": HealthStatus.UNKNOWN,
                "message": "No targets configured",
                "targets_checked": 0,
                "results": []
            }

        # Run health checks concurrently
        logger.info(f"[{self.name}] Checking {len(targets_to_check)} target(s)")
        tasks = [self._check_target(target) for target in targets_to_check]
        results = await asyncio.gather(*tasks)

        # Determine overall status
        statuses = [r["status"] for r in results]
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.UNKNOWN

        # Build summary
        summary = {
            "overall_status": overall_status,
            "targets_checked": len(results),
            "healthy": sum(1 for r in results if r["status"] == HealthStatus.HEALTHY),
            "degraded": sum(1 for r in results if r["status"] == HealthStatus.DEGRADED),
            "unhealthy": sum(1 for r in results if r["status"] == HealthStatus.UNHEALTHY),
            "unknown": sum(1 for r in results if r["status"] == HealthStatus.UNKNOWN),
            "results": results
        }

        # Add to history
        history_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": overall_status,
            "targets_checked": len(results),
            "summary": {
                "healthy": summary["healthy"],
                "degraded": summary["degraded"],
                "unhealthy": summary["unhealthy"]
            }
        }
        self._history.append(history_entry)

        # Trim history if needed
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        return summary


# Singleton instance
health_monitor_agent = HealthMonitorAgent()
