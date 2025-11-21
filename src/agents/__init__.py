"""
Agents module - AI Agents for various tasks
"""

from src.agents.base import BaseAgent
from src.agents.health_monitor import HealthMonitorAgent
from src.agents.stock_monitor import StockMonitorAgent
from src.agents.claude_agent import ClaudeAgent
from src.agents.news_search import NewsSearchAgent

__all__ = ["BaseAgent", "HealthMonitorAgent", "StockMonitorAgent", "ClaudeAgent", "NewsSearchAgent"]
