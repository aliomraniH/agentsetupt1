"""
API routes for agents
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from loguru import logger

from src.agents import HealthMonitorAgent, StockMonitorAgent, NewsSearchAgent
from src.agents.health_monitor import health_monitor_agent, ServiceType
from src.agents.stock_monitor import stock_monitor_agent
from src.agents.news_search import news_search_agent
from src.core.config import settings

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


class RunNewsSearchRequest(BaseModel):
    """Request to search news"""
    symbols: Optional[List[str]] = None
    company_names: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    max_results_per_source: int = 3


# ============== Agent Management ==============

@router.get("/agents")
async def list_agents():
    """
    List all available agents.
    Returns information about each agent.
    """
    agents = [
        health_monitor_agent.get_info(),
        stock_monitor_agent.get_info(),
        news_search_agent.get_info()
    ]
    return {
        "count": len(agents),
        "agents": agents
    }


# ============== LLM API Test Endpoint (Must be before {agent_name} route) ==============

@router.get("/agents/llm-test")
async def test_llm_api():
    """
    Test Anthropic/Claude API with simple questions that have known answers.

    Verifies:
    - API key is configured correctly
    - API is responding to requests
    - Responses are accurate
    """
    logger.info("="*80)
    logger.info("🧪 CLAUDE API TEST - Starting verification")
    logger.info("="*80)

    # Check API key
    if not settings.anthropic_api_key:
        logger.error("❌ ANTHROPIC_API_KEY not configured")
        return {
            "status": "error",
            "error": "ANTHROPIC_API_KEY not configured in Replit Secrets",
            "message": "Add your Anthropic API key to Replit Secrets as ANTHROPIC_API_KEY"
        }

    logger.info(f"✓ API key found: {settings.anthropic_api_key[:20]}...")

    # Import Anthropic
    try:
        from anthropic import Anthropic
        logger.info("✓ Anthropic library loaded")
    except ImportError:
        logger.error("❌ Anthropic library not installed")
        return {
            "status": "error",
            "error": "Anthropic library missing",
            "message": "Library not found. Redeploy to install dependencies."
        }

    # Test questions
    tests = [
        {"id": "geo_1", "q": "What is the capital of France? Reply with only the city name.", "expect": "Paris", "category": "geography"},
        {"id": "geo_2", "q": "What is the capital of Japan? Reply with only the city name.", "expect": "Tokyo", "category": "geography"},
        {"id": "color_1", "q": "What color is the sky on a clear day? Reply with only the color.", "expect": "blue", "category": "colors"},
        {"id": "color_2", "q": "What color are ripe bananas? Reply with only the color.", "expect": "yellow", "category": "colors"},
        {"id": "math_1", "q": "What is 7 + 5? Reply with only the number.", "expect": "12", "category": "math"}
    ]

    results = []
    passed = failed = 0

    logger.info(f"\n📝 Running {len(tests)} test questions...")
    logger.info("-"*80)

    try:
        # Initialize client
        client = Anthropic(api_key=settings.anthropic_api_key)
        logger.info("✓ Client initialized")

        # Run tests
        for i, test in enumerate(tests, 1):
            logger.info(f"\n🔍 Test {i}/{len(tests)}: {test['q'][:50]}...")
            logger.info(f"   Expected: {test['expect']}")

            try:
                # Call Claude API - FIXED MODEL NAME
                response = client.messages.create(
                    model="claude-3-5-sonnet-20240620",  # Correct model name
                    max_tokens=50,
                    temperature=0,
                    messages=[{"role": "user", "content": test['q']}]
                )

                answer = response.content[0].text.strip()
                logger.info(f"   Response: {answer}")

                # Check answer
                is_correct = test['expect'].lower() in answer.lower()

                if is_correct:
                    logger.success(f"   ✅ PASSED")
                    passed += 1
                    result = "passed"
                else:
                    logger.error(f"   ❌ FAILED")
                    failed += 1
                    result = "failed"

                results.append({
                    "test_id": test['id'],
                    "question": test['q'],
                    "expected": test['expect'],
                    "actual": answer,
                    "result": result,
                    "category": test['category']
                })

            except Exception as e:
                logger.error(f"   ❌ ERROR: {e}")
                failed += 1
                results.append({
                    "test_id": test['id'],
                    "question": test['q'],
                    "expected": test['expect'],
                    "actual": None,
                    "error": str(e),
                    "result": "error",
                    "category": test['category']
                })

        # Summary
        logger.info("\n" + "="*80)
        logger.info("📊 TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Total:   {len(tests)}")
        logger.info(f"✅ Pass:  {passed}")
        logger.info(f"❌ Fail:  {failed}")
        logger.info(f"Rate:    {(passed/len(tests)*100):.1f}%")
        logger.info("="*80)

        status = "success" if failed == 0 else "partial" if passed > 0 else "error"

        return {
            "status": status,
            "summary": {
                "total_tests": len(tests),
                "passed": passed,
                "failed": failed,
                "success_rate": round(passed / len(tests) * 100, 1)
            },
            "tests": results,
            "message": f"All {passed} tests passed! Claude API working." if failed == 0 else f"{failed} test(s) failed."
        }

    except Exception as e:
        logger.error(f"\n❌ CRITICAL: {e}")
        logger.exception("Traceback:")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to connect to Claude API. Check API key.",
            "tests": results
        }


@router.get("/agents/{agent_name}")
async def get_agent_info(agent_name: str):
    """
    Get information about a specific agent.

    NOTE: This route must be defined AFTER all specific routes to avoid conflicts.
    """
    if agent_name == "health-monitor":
        return health_monitor_agent.get_info()
    elif agent_name == "stock-monitor":
        return stock_monitor_agent.get_info()
    elif agent_name == "news-search":
        return news_search_agent.get_info()

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
async def quick_stock_check(
    skip_cache: bool = False,
    debug: bool = False
):
    """
    Quick check of top tech stocks.

    Convenience endpoint that returns top 10 tech stocks immediately.
    Ideal for quick queries from Claude Chat.

    Args:
        skip_cache: Set to true to bypass cache and fetch fresh data
        debug: Set to true to include debug metadata (data sources, validations, etc.)
    """
    result = await stock_monitor_agent.execute(
        category="top_tech",
        skip_cache=skip_cache,
        debug=debug
    )
    return result


# ============== News Search Agent ==============

@router.post("/agents/news-search/run")
async def run_news_search(request: RunNewsSearchRequest = None):
    """
    Search for stock-related news and videos.

    Use this endpoint from Claude Chat to find recent news about stocks.

    Sources:
    - YouTube: Recent videos
    - New York Times: News articles
    - Wall Street Journal: Financial news

    You can search by:
    - Stock symbols (AAPL, GOOGL, etc.)
    - Company names (Apple, Google, etc.)

    Returns relevant links from the past few days.
    """
    if request:
        result = await news_search_agent.execute(
            symbols=request.symbols,
            company_names=request.company_names,
            sources=request.sources,
            max_results_per_source=request.max_results_per_source
        )
    else:
        result = await news_search_agent.execute()
    return result


@router.get("/agents/news-search/status")
async def get_news_search_status():
    """
    Get the current status and last result of the news search agent.
    """
    info = news_search_agent.get_info()
    info["last_result"] = news_search_agent.last_result
    return info


@router.get("/agents/news-search/quick")
async def quick_news_search(symbols: str = "AAPL,GOOGL,MSFT"):
    """
    Quick news search for specified symbols.

    Usage: /agents/news-search/quick?symbols=AAPL,GOOGL,TSLA

    Default: Top tech stocks (AAPL, GOOGL, MSFT)
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    result = await news_search_agent.execute(symbols=symbol_list)
    return result
