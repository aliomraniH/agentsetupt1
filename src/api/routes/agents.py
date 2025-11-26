"""
API routes for agents
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from loguru import logger

from src.agents import HealthMonitorAgent, StockMonitorAgent, ClaudeAgent, NewsSearchAgent
from src.agents.health_monitor import health_monitor_agent, ServiceType
from src.agents.stock_monitor import stock_monitor_agent
from src.agents.claude_agent import claude_agent, ClaudeModel
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


class ClaudeRequest(BaseModel):
    """Request to Claude AI"""
    message: str
    task: str = "chat"
    model: str = "claude-3-5-sonnet-20241022"  # Latest Claude 3.5 Sonnet v2 (with auto-fallback)
    system_prompt: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 1.0
    use_conversation_history: bool = False


class ClaudeChatRequest(BaseModel):
    """Simple chat request"""
    message: str
    model: str = "claude-3-5-sonnet-20241022"  # Latest Claude 3.5 Sonnet v2 (with auto-fallback)


class ClaudeCodeReviewRequest(BaseModel):
    """Code review request"""
    code: str
    language: str = "python"
    model: str = "claude-3-5-sonnet-20241022"  # Latest Claude 3.5 Sonnet v2 (with auto-fallback)


class ClaudeCodeGenerateRequest(BaseModel):
    """Code generation request"""
    requirements: str
    language: str = "python"
    model: str = "claude-3-5-sonnet-20241022"  # Latest Claude 3.5 Sonnet v2 (with auto-fallback)


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
        claude_agent.get_info(),
        news_search_agent.get_info()
    ]
    return {
        "count": len(agents),
        "agents": agents
    }


@router.get("/agents/debug-keys")
async def debug_api_keys():
    """
    Debug endpoint to check API key configuration.

    Verifies that API keys are correctly loaded from Replit Secrets.
    Shows which keys are present in environment vs loaded into settings.
    """
    import os

    # Check environment variables directly
    env_anthropic = os.environ.get("ANTHROPIC_API_KEY")
    env_alpha = os.environ.get("ALPHA_VANTAGE_API_KEY")
    env_perplexity = os.environ.get("PERPLEXITY_API_KEY")

    return {
        "environment_variables": {
            "ANTHROPIC_API_KEY": "✅ Present" if env_anthropic else "❌ Not found",
            "ALPHA_VANTAGE_API_KEY": "✅ Present" if env_alpha else "❌ Not found",
            "PERPLEXITY_API_KEY": "✅ Present" if env_perplexity else "❌ Not found"
        },
        "settings_loaded": {
            "anthropic_api_key": "✅ Loaded" if settings.anthropic_api_key else "❌ Not loaded",
            "alpha_vantage_api_key": "✅ Loaded" if settings.alpha_vantage_api_key else "❌ Not loaded",
            "perplexity_api_key": "✅ Loaded" if settings.perplexity_api_key else "❌ Not loaded"
        },
        "key_previews": {
            "anthropic": f"{settings.anthropic_api_key[:15]}...{settings.anthropic_api_key[-4:]}" if settings.anthropic_api_key and len(settings.anthropic_api_key) > 20 else "N/A",
            "alpha_vantage": f"{settings.alpha_vantage_api_key[:10]}...{settings.alpha_vantage_api_key[-4:]}" if settings.alpha_vantage_api_key and len(settings.alpha_vantage_api_key) > 15 else "N/A",
            "perplexity": f"{settings.perplexity_api_key[:15]}...{settings.perplexity_api_key[-4:]}" if settings.perplexity_api_key and len(settings.perplexity_api_key) > 20 else "N/A"
        },
        "config": {
            "case_sensitive": "True (required for Replit Secrets)",
            "env_file": ".env"
        }
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
    import os

    logger.info("="*80)
    logger.info("🧪 CLAUDE API TEST - Starting verification")
    logger.info("="*80)

    # Direct environment check (bypass pydantic)
    direct_env_key = os.environ.get("ANTHROPIC_API_KEY")
    logger.info(f"🔍 Direct environment check: {'✅ Found' if direct_env_key else '❌ Not found'}")
    if direct_env_key:
        logger.info(f"   Key preview: {direct_env_key[:20]}...")

    # Check settings (pydantic-loaded)
    logger.info(f"🔍 Settings check: {'✅ Loaded' if settings.anthropic_api_key else '❌ Not loaded'}")

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
            "error": "anthropic package not installed",
            "message": "Install with: pip install anthropic"
        }

    # Initialize client
    try:
        client = Anthropic(api_key=settings.anthropic_api_key)
        logger.info("✓ Anthropic client initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize client: {e}")
        return {
            "status": "error",
            "error": f"Failed to initialize Anthropic client: {str(e)}"
        }

    # Test questions with expected answers
    test_questions = [
        {"id": "geo_1", "question": "What is the capital of France?", "expected": "Paris", "category": "geography"},
        {"id": "colors_1", "question": "What color is the sky on a clear day?", "expected": "blue", "category": "colors"},
        {"id": "math_1", "question": "What is 2 + 2?", "expected": "4", "category": "math"},
        {"id": "geo_2", "question": "What is the largest ocean?", "expected": "Pacific", "category": "geography"},
        {"id": "basic_1", "question": "How many days are in a week?", "expected": "7", "category": "basic"}
    ]

    results = []
    passed = 0
    failed = 0

    logger.info(f"Running {len(test_questions)} tests...")

    for test in test_questions:
        logger.info(f"\n📝 Test: {test['id']} ({test['category']})")
        logger.info(f"Question: {test['question']}")

        try:
            # Make API call
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Latest Sonnet v2 (with auto-fallback to v1)
                max_tokens=50,
                temperature=0,  # Deterministic for testing
                messages=[{"role": "user", "content": test["question"]}]
            )

            # Extract answer
            answer = response.content[0].text.strip()
            logger.info(f"Answer: {answer}")

            # Check if answer contains expected text (case-insensitive)
            is_correct = test["expected"].lower() in answer.lower()

            if is_correct:
                logger.info(f"✅ PASSED")
                passed += 1
                result_status = "passed"
            else:
                logger.warning(f"❌ FAILED - Expected '{test['expected']}' in answer")
                failed += 1
                result_status = "failed"

            results.append({
                "test_id": test["id"],
                "question": test["question"],
                "expected": test["expected"],
                "actual": answer,
                "result": result_status,
                "category": test["category"]
            })

        except Exception as e:
            logger.error(f"❌ FAILED - API Error: {e}")
            failed += 1
            results.append({
                "test_id": test["id"],
                "question": test["question"],
                "expected": test["expected"],
                "actual": None,
                "result": "error",
                "error": str(e),
                "category": test["category"]
            })

    # Summary
    logger.info("\n" + "="*80)
    logger.info(f"TEST SUMMARY: {passed}/{len(test_questions)} passed")
    logger.info("="*80)

    success_rate = (passed / len(test_questions)) * 100

    if passed == len(test_questions):
        message = f"All {passed} tests passed! Claude API working."
    elif passed > 0:
        message = f"{passed}/{len(test_questions)} tests passed. Some issues detected."
    else:
        message = "All tests failed. Check API key and configuration."

    return {
        "status": "success" if passed == len(test_questions) else "partial",
        "summary": {
            "total_tests": len(test_questions),
            "passed": passed,
            "failed": failed,
            "success_rate": success_rate
        },
        "tests": results,
        "message": message
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
    elif agent_name == "claude-assistant":
        return claude_agent.get_info()
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
async def quick_stock_check():
    """
    Quick check of top tech stocks.

    Convenience endpoint that returns top 10 tech stocks immediately.
    Ideal for quick queries from Claude Chat.
    """
    result = await stock_monitor_agent.execute(category="top_tech")
    return result


# ============== Claude AI Agent ==============

@router.post("/agents/claude-assistant/run")
async def run_claude_task(request: ClaudeRequest):
    """
    Execute a Claude AI task.

    Available tasks:
    - chat: General conversation (supports history)
    - analyze: Analyze and provide insights
    - summarize: Summarize content
    - code_review: Review code for issues
    - code_generate: Generate code from requirements
    - translate: Translate text
    - custom: Use custom system prompt

    Models available:
    - claude-3-5-sonnet-20241022 (recommended, latest v2 with auto-fallback) ✅ DEFAULT
    - claude-3-5-sonnet-20240620 (stable v1 fallback)
    - claude-3-opus-20240229 (most capable)
    - claude-3-5-haiku-20241022 (fastest, most economical)
    """
    try:
        result = await claude_agent.execute(
            message=request.message,
            task=request.task,
            model=request.model,
            system_prompt=request.system_prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            use_conversation_history=request.use_conversation_history
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/claude-assistant/chat")
async def claude_chat(request: ClaudeChatRequest):
    """
    Simple chat with Claude.

    Maintains conversation history automatically.
    Perfect for interactive conversations.
    """
    try:
        result = await claude_agent.execute(
            message=request.message,
            task="chat",
            model=request.model,
            use_conversation_history=True
        )
        return {
            "response": result["result"]["response"],
            "usage": result["result"]["usage"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/claude-assistant/analyze")
async def claude_analyze(request: ClaudeChatRequest):
    """
    Analyze text and provide insights.
    """
    try:
        result = await claude_agent.execute(
            message=request.message,
            task="analyze",
            model=request.model
        )
        return {
            "analysis": result["result"]["response"],
            "usage": result["result"]["usage"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/claude-assistant/summarize")
async def claude_summarize(request: ClaudeChatRequest):
    """
    Summarize text content.
    """
    try:
        result = await claude_agent.execute(
            message=request.message,
            task="summarize",
            model=request.model
        )
        return {
            "summary": result["result"]["response"],
            "usage": result["result"]["usage"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/claude-assistant/code/review")
async def claude_code_review(request: ClaudeCodeReviewRequest):
    """
    Review code for bugs, security issues, and best practices.
    """
    try:
        result = await claude_agent.execute(
            message=f"Review this {request.language} code:\n\n```{request.language}\n{request.code}\n```",
            task="code_review",
            model=request.model
        )
        return {
            "review": result["result"]["response"],
            "usage": result["result"]["usage"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/claude-assistant/code/generate")
async def claude_code_generate(request: ClaudeCodeGenerateRequest):
    """
    Generate code based on requirements.
    """
    try:
        result = await claude_agent.execute(
            message=f"Generate {request.language} code for the following requirements:\n\n{request.requirements}",
            task="code_generate",
            model=request.model
        )
        return {
            "code": result["result"]["response"],
            "usage": result["result"]["usage"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/claude-assistant/status")
async def get_claude_status():
    """
    Get the current status and last result of the Claude agent.
    """
    info = claude_agent.get_info()
    info["last_result"] = claude_agent.last_result
    return info


@router.get("/agents/claude-assistant/history")
async def get_claude_history():
    """
    Get conversation history.
    """
    return {
        "history": claude_agent.get_history()
    }


@router.post("/agents/claude-assistant/history/clear")
async def clear_claude_history():
    """
    Clear conversation history.
    """
    claude_agent.clear_history()
    return {
        "status": "success",
        "message": "Conversation history cleared"
    }


@router.get("/agents/claude-assistant/models")
async def get_available_models():
    """
    Get available Claude models.
    """
    return {
        "models": [
            {
                "id": ClaudeModel.SONNET.value,
                "name": "Claude 3.5 Sonnet",
                "description": "Balanced performance and speed (recommended)",
                "recommended": True
            },
            {
                "id": ClaudeModel.OPUS.value,
                "name": "Claude 3 Opus",
                "description": "Most capable model for complex tasks"
            },
            {
                "id": ClaudeModel.HAIKU.value,
                "name": "Claude 3.5 Haiku",
                "description": "Fastest and most economical"
            }
        ]
    }


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
