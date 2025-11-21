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


# ============== LLM API Test Endpoints (Must be before {agent_name} route) ==============

@router.get("/agents/llm-test")
async def test_llm_api():
    """
    Test Perplexity LLM API with simple questions that have known answers.

    This endpoint verifies that:
    1. The API key is configured correctly
    2. The API is responding to requests
    3. The responses are accurate

    Tests include:
    - Capital cities of countries
    - Colors of common objects
    - Basic factual questions
    """
    logger.info("="*80)
    logger.info("🧪 LLM API TEST - Starting Perplexity API verification")
    logger.info("="*80)

    # Check if API key is configured
    if not settings.perplexity_api_key:
        logger.error("❌ Perplexity API key not configured")
        return {
            "status": "error",
            "error": "PERPLEXITY_API_KEY not configured in Replit Secrets",
            "message": "Please add your Perplexity API key to Replit Secrets"
        }

    logger.info(f"✓ API key found: {settings.perplexity_api_key[:15]}...")

    # Import OpenAI client
    try:
        from openai import OpenAI
        logger.info("✓ OpenAI library imported successfully")
    except ImportError:
        logger.error("❌ OpenAI library not installed")
        return {
            "status": "error",
            "error": "OpenAI library not installed",
            "message": "Run: pip install openai"
        }

    # Test questions with known answers
    test_questions = [
        {
            "id": "capitals_1",
            "question": "What is the capital of France?",
            "expected_answer": "Paris",
            "category": "geography"
        },
        {
            "id": "capitals_2",
            "question": "What is the capital of Japan?",
            "expected_answer": "Tokyo",
            "category": "geography"
        },
        {
            "id": "colors_1",
            "question": "What color is the sky on a clear day?",
            "expected_answer": "blue",
            "category": "colors"
        },
        {
            "id": "colors_2",
            "question": "What color are bananas when they are ripe?",
            "expected_answer": "yellow",
            "category": "colors"
        },
        {
            "id": "facts_1",
            "question": "How many continents are there on Earth?",
            "expected_answer": "7",
            "category": "facts"
        }
    ]

    results = []
    passed = 0
    failed = 0

    logger.info(f"\n📝 Running {len(test_questions)} test questions...")
    logger.info("-"*80)

    try:
        # Initialize Perplexity client
        client = OpenAI(
            api_key=settings.perplexity_api_key,
            base_url="https://api.perplexity.ai"
        )
        logger.info("✓ Perplexity client initialized")

        # Run each test question
        for i, test in enumerate(test_questions, 1):
            logger.info(f"\n🔍 Test {i}/{len(test_questions)}: {test['question']}")
            logger.info(f"   Expected: {test['expected_answer']}")

            try:
                # Make API call
                response = client.chat.completions.create(
                    model="llama-3.1-sonar-small-128k-online",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant. Answer questions concisely with just the answer, no explanations."
                        },
                        {
                            "role": "user",
                            "content": test['question']
                        }
                    ],
                    temperature=0.0,
                    max_tokens=50
                )

                answer = response.choices[0].message.content.strip()
                logger.info(f"   Response: {answer}")

                # Check if answer is correct (case-insensitive contains)
                expected_lower = test['expected_answer'].lower()
                answer_lower = answer.lower()

                is_correct = expected_lower in answer_lower

                if is_correct:
                    logger.success(f"   ✅ PASSED - Answer contains '{test['expected_answer']}'")
                    passed += 1
                    test_result = "passed"
                else:
                    logger.error(f"   ❌ FAILED - Expected '{test['expected_answer']}' but got '{answer}'")
                    failed += 1
                    test_result = "failed"

                results.append({
                    "test_id": test['id'],
                    "question": test['question'],
                    "expected": test['expected_answer'],
                    "actual": answer,
                    "result": test_result,
                    "category": test['category']
                })

            except Exception as e:
                logger.error(f"   ❌ ERROR: {type(e).__name__}: {e}")
                failed += 1
                results.append({
                    "test_id": test['id'],
                    "question": test['question'],
                    "expected": test['expected_answer'],
                    "actual": None,
                    "error": str(e),
                    "result": "error",
                    "category": test['category']
                })

        # Summary
        logger.info("\n" + "="*80)
        logger.info("📊 TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Total Tests:  {len(test_questions)}")
        logger.info(f"✅ Passed:     {passed}")
        logger.info(f"❌ Failed:     {failed}")
        logger.info(f"Success Rate: {(passed/len(test_questions)*100):.1f}%")
        logger.info("="*80)

        overall_status = "success" if failed == 0 else "partial" if passed > 0 else "error"

        return {
            "status": overall_status,
            "summary": {
                "total_tests": len(test_questions),
                "passed": passed,
                "failed": failed,
                "success_rate": round(passed / len(test_questions) * 100, 1)
            },
            "tests": results,
            "message": "All tests passed! Perplexity API is working correctly." if failed == 0 else f"{failed} test(s) failed. Check the logs for details."
        }

    except Exception as e:
        logger.error(f"\n❌ CRITICAL ERROR: {type(e).__name__}: {e}")
        logger.exception("Full traceback:")
        return {
            "status": "error",
            "error": f"{type(e).__name__}: {str(e)}",
            "message": "Failed to connect to Perplexity API. Check API key and network connection.",
            "tests": results
        }


@router.get("/agents/anthropic-test")
async def test_anthropic_api():
    """
    Test Anthropic/Claude API with simple questions that have known answers.

    This endpoint verifies that:
    1. The API key is configured correctly
    2. The API is responding to requests
    3. The responses are accurate

    Tests include:
    - Capital cities of countries
    - Colors of common objects
    - Basic factual questions
    """
    logger.info("="*80)
    logger.info("🧪 ANTHROPIC API TEST - Starting Claude API verification")
    logger.info("="*80)

    # Check if API key is configured
    if not settings.anthropic_api_key:
        logger.error("❌ Anthropic API key not configured")
        return {
            "status": "error",
            "error": "ANTHROPIC_API_KEY not configured in Replit Secrets",
            "message": "Please add your Anthropic API key to Replit Secrets with key name: ANTHROPIC_API_KEY"
        }

    logger.info(f"✓ API key found: {settings.anthropic_api_key[:15]}...")

    # Import Anthropic client
    try:
        from anthropic import Anthropic
        logger.info("✓ Anthropic library imported successfully")
    except ImportError:
        logger.error("❌ Anthropic library not installed")
        return {
            "status": "error",
            "error": "Anthropic library not installed",
            "message": "Run: pip install anthropic"
        }

    # Test questions with known answers
    test_questions = [
        {
            "id": "capitals_1",
            "question": "What is the capital of France? Reply with only the city name.",
            "expected_answer": "Paris",
            "category": "geography"
        },
        {
            "id": "capitals_2",
            "question": "What is the capital of Japan? Reply with only the city name.",
            "expected_answer": "Tokyo",
            "category": "geography"
        },
        {
            "id": "colors_1",
            "question": "What color is the sky on a clear day? Reply with only the color.",
            "expected_answer": "blue",
            "category": "colors"
        },
        {
            "id": "colors_2",
            "question": "What color are bananas when they are ripe? Reply with only the color.",
            "expected_answer": "yellow",
            "category": "colors"
        },
        {
            "id": "math_1",
            "question": "What is 7 + 5? Reply with only the number.",
            "expected_answer": "12",
            "category": "math"
        }
    ]

    results = []
    passed = 0
    failed = 0

    logger.info(f"\n📝 Running {len(test_questions)} test questions...")
    logger.info("-"*80)

    try:
        # Initialize Anthropic client
        client = Anthropic(api_key=settings.anthropic_api_key)
        logger.info("✓ Anthropic client initialized")

        # Run each test question
        for i, test in enumerate(test_questions, 1):
            logger.info(f"\n🔍 Test {i}/{len(test_questions)}: {test['question']}")
            logger.info(f"   Expected: {test['expected_answer']}")

            try:
                # Make API call to Claude
                message = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=50,
                    temperature=0.0,
                    messages=[
                        {
                            "role": "user",
                            "content": test['question']
                        }
                    ]
                )

                answer = message.content[0].text.strip()
                logger.info(f"   Response: {answer}")

                # Check if answer is correct (case-insensitive contains)
                expected_lower = test['expected_answer'].lower()
                answer_lower = answer.lower()

                is_correct = expected_lower in answer_lower

                if is_correct:
                    logger.success(f"   ✅ PASSED - Answer contains '{test['expected_answer']}'")
                    passed += 1
                    test_result = "passed"
                else:
                    logger.error(f"   ❌ FAILED - Expected '{test['expected_answer']}' but got '{answer}'")
                    failed += 1
                    test_result = "failed"

                results.append({
                    "test_id": test['id'],
                    "question": test['question'],
                    "expected": test['expected_answer'],
                    "actual": answer,
                    "result": test_result,
                    "category": test['category']
                })

            except Exception as e:
                logger.error(f"   ❌ ERROR: {type(e).__name__}: {e}")
                failed += 1
                results.append({
                    "test_id": test['id'],
                    "question": test['question'],
                    "expected": test['expected_answer'],
                    "actual": None,
                    "error": str(e),
                    "result": "error",
                    "category": test['category']
                })

        # Summary
        logger.info("\n" + "="*80)
        logger.info("📊 TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Total Tests:  {len(test_questions)}")
        logger.info(f"✅ Passed:     {passed}")
        logger.info(f"❌ Failed:     {failed}")
        logger.info(f"Success Rate: {(passed/len(test_questions)*100):.1f}%")
        logger.info("="*80)

        overall_status = "success" if failed == 0 else "partial" if passed > 0 else "error"

        return {
            "status": overall_status,
            "summary": {
                "total_tests": len(test_questions),
                "passed": passed,
                "failed": failed,
                "success_rate": round(passed / len(test_questions) * 100, 1)
            },
            "tests": results,
            "message": "All tests passed! Anthropic API is working correctly." if failed == 0 else f"{failed} test(s) failed. Check the logs for details."
        }

    except Exception as e:
        logger.error(f"\n❌ CRITICAL ERROR: {type(e).__name__}: {e}")
        logger.exception("Full traceback:")
        return {
            "status": "error",
            "error": f"{type(e).__name__}: {str(e)}",
            "message": "Failed to connect to Anthropic API. Check API key and network connection.",
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
