"""
Base Agent class that all agents inherit from
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from enum import Enum
from loguru import logger
import uuid


class AgentStatus(str, Enum):
    """Agent execution status"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BaseAgent(ABC):
    """
    Base class for all agents.

    All agents must implement:
    - name: Agent identifier
    - description: What the agent does
    - run(): Main execution method
    """

    def __init__(self):
        self._status = AgentStatus.IDLE
        self._last_run: Optional[datetime] = None
        self._last_result: Optional[Dict[str, Any]] = None
        self._run_count: int = 0
        self._error_count: int = 0

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name/identifier"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Agent description"""
        pass

    @property
    def status(self) -> AgentStatus:
        """Current agent status"""
        return self._status

    @property
    def last_run(self) -> Optional[datetime]:
        """Timestamp of last run"""
        return self._last_run

    @property
    def last_result(self) -> Optional[Dict[str, Any]]:
        """Result from last run"""
        return self._last_result

    @property
    def stats(self) -> Dict[str, Any]:
        """Agent statistics"""
        return {
            "run_count": self._run_count,
            "error_count": self._error_count,
            "success_rate": (
                (self._run_count - self._error_count) / self._run_count * 100
                if self._run_count > 0 else 0
            )
        }

    @abstractmethod
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Main execution method for the agent.
        Must be implemented by subclasses.

        Returns:
            Dict containing the result of the agent's work
        """
        pass

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the agent with proper status tracking and error handling.
        This is the public method to call the agent.
        """
        run_id = str(uuid.uuid4())[:8]
        logger.info(f"[{self.name}] Starting execution (run_id: {run_id})")

        self._status = AgentStatus.RUNNING
        start_time = datetime.now(timezone.utc)

        try:
            result = await self.run(**kwargs)

            self._status = AgentStatus.COMPLETED
            self._run_count += 1
            self._last_run = datetime.now(timezone.utc)

            execution_time = (self._last_run - start_time).total_seconds()

            self._last_result = {
                "run_id": run_id,
                "agent": self.name,
                "status": "success",
                "started_at": start_time.isoformat(),
                "completed_at": self._last_run.isoformat(),
                "execution_time_seconds": execution_time,
                "result": result
            }

            logger.info(f"[{self.name}] Completed successfully in {execution_time:.2f}s")
            return self._last_result

        except Exception as e:
            self._status = AgentStatus.FAILED
            self._run_count += 1
            self._error_count += 1
            self._last_run = datetime.now(timezone.utc)

            execution_time = (self._last_run - start_time).total_seconds()

            self._last_result = {
                "run_id": run_id,
                "agent": self.name,
                "status": "error",
                "started_at": start_time.isoformat(),
                "completed_at": self._last_run.isoformat(),
                "execution_time_seconds": execution_time,
                "error": str(e)
            }

            logger.error(f"[{self.name}] Failed: {e}")
            return self._last_result

    def get_info(self) -> Dict[str, Any]:
        """Get agent information and current state"""
        return {
            "name": self.name,
            "description": self.description,
            "status": self._status.value,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "stats": self.stats
        }
