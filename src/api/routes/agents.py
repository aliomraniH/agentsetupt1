"""
API routes for agents
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional

from src.agents import HealthMonitorAgent, StockMonitorAgent
from src.agents.health_monitor import health_monitor_agent, ServiceType
from src.agents.stock_monitor import stock_monitor_agent

router = APIRouter()


# Request/Response models
class RunHealthCheckRequest(BaseModel):
    """Request to run health check"""
    target_ids: Optional[List[str]] = None


class AddTargetRequest(BaseModel):
    """Request to add a monitoring target"""
    target_id: str
    name: str
    url: str
    service_type: str = "external"
    timeout: int = 30
    enabled: bool = True


class RunStockCheckRequest(BaseModel):
    """Request to run stock check"""
    category: str = "top_tech"
    symbols: Optional[List[str]] = None


# ============== Agent Management ==============

@router.get("/agents")
async def list_agents():
    """
    List all available agents.
    Returns information about each agent.
    """
    agents = [
        health_monitor_agent.get_info(),
        stock_monitor_agent.get_info()
    ]
    return {
        "count": len(agents),
        "agents": agents
    }


@router.get("/agents/{agent_name}")
async def get_agent_info(agent_name: str):
    """
    Get information about a specific agent.
    """
    if agent_name == "health-monitor":
        return health_monitor_agent.get_info()
    elif agent_name == "stock-monitor":
        return stock_monitor_agent.get_info()

    raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")


# ============== Health Monitor Agent ==============

@router.post("/agents/health-monitor/run")
async def run_health_check(request: RunHealthCheckRequest = None):
    """
    Trigger a health check run.

    Optionally specify target_ids to check specific targets.
    If not specified, checks all enabled targets.
    """
    target_ids = request.target_ids if request else None
    result = await health_monitor_agent.execute(target_ids=target_ids)
    return result


@router.get("/agents/health-monitor/status")
async def get_health_monitor_status():
    """
    Get the current status and last result of the health monitor agent.
    """
    info = health_monitor_agent.get_info()
    info["last_result"] = health_monitor_agent.last_result
    return info


@router.get("/agents/health-monitor/history")
async def get_health_check_history(limit: int = 10):
    """
    Get health check history.

    Args:
        limit: Maximum number of history entries to return (default: 10)
    """
    history = health_monitor_agent.get_history(limit=limit)
    return {
        "count": len(history),
        "history": history
    }


@router.get("/agents/health-monitor/targets")
async def get_monitoring_targets():
    """
    Get all configured monitoring targets.
    """
    targets = health_monitor_agent.get_targets()
    return {
        "count": len(targets),
        "targets": targets
    }


@router.post("/agents/health-monitor/targets")
async def add_monitoring_target(request: AddTargetRequest):
    """
    Add a new monitoring target.

    This allows you to dynamically add services to monitor.
    """
    try:
        # Map string to ServiceType enum
        try:
            service_type = ServiceType(request.service_type)
        except ValueError:
            service_type = ServiceType.EXTERNAL

        target = health_monitor_agent.add_target(
            target_id=request.target_id,
            name=request.name,
            url=request.url,
            service_type=service_type,
            timeout=request.timeout,
            enabled=request.enabled
        )
        return {
            "status": "success",
            "message": f"Target '{request.target_id}' added successfully",
            "target": target
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/agents/health-monitor/targets/{target_id}")
async def remove_monitoring_target(target_id: str):
    """
    Remove a monitoring target.

    Note: Cannot remove the default backend self-check.
    """
    try:
        removed = health_monitor_agent.remove_target(target_id)
        if removed:
            return {
                "status": "success",
                "message": f"Target '{target_id}' removed successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Target '{target_id}' not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============== Stock Monitor Agent ==============

@router.post("/agents/stock-monitor/run")
async def run_stock_check(request: RunStockCheckRequest = None):
    """
    Fetch top stock data.

    Use this endpoint from Claude Chat or other services to get real-time stock information.

    Categories available:
    - top_tech: Top 10 tech stocks (AAPL, MSFT, GOOGL, etc.)
    - top_sp500: Top S&P 500 by market cap
    - top_diversified: Diversified portfolio mix

    Or provide custom symbols list.
    """
    if request:
        result = await stock_monitor_agent.execute(
            category=request.category,
            symbols=request.symbols
        )
    else:
        result = await stock_monitor_agent.execute()
    return result


@router.get("/agents/stock-monitor/status")
async def get_stock_monitor_status():
    """
    Get the current status and last result of the stock monitor agent.
    """
    info = stock_monitor_agent.get_info()
    info["last_result"] = stock_monitor_agent.last_result
    return info


@router.get("/agents/stock-monitor/lists")
async def get_available_stock_lists():
    """
    Get available pre-defined stock lists.

    Returns the categories you can use with the run endpoint.
    """
    return {
        "lists": stock_monitor_agent.get_available_lists()
    }


@router.get("/agents/stock-monitor/quick")
async def quick_stock_check():
    """
    Quick check of top tech stocks.

    Convenience endpoint that returns top 10 tech stocks immediately.
    Ideal for quick queries from Claude Chat.
    """
    result = await stock_monitor_agent.execute(category="top_tech")
    return result
