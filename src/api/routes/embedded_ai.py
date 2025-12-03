"""
API routes for embedded AI agents

These endpoints are specifically designed for embedded AI agent usage,
making it clear when third-party applications are using our embedded
Claude responses vs their own AI agents.
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger

from src.agents.stock_monitor import stock_monitor_agent
from src.agents.news_search import news_search_agent
from src.agents.claude_agent import claude_agent, ClaudeModel
from src.core.api_logger import api_logger, ClaudeUsageType

router = APIRouter()


# Request models
class StockQueryRequest(BaseModel):
    """Request for stock data with embedded AI formatting"""
    symbols: Optional[List[str]] = None
    category: str = "top_tech"
    include_ai_summary: bool = True
    query_context: Optional[str] = None  # User's original query


class NewsQueryRequest(BaseModel):
    """Request for news with embedded AI formatting"""
    symbols: Optional[List[str]] = None
    company_names: Optional[List[str]] = None
    query_context: Optional[str] = None  # User's original query


class AIAnalysisRequest(BaseModel):
    """Request for AI analysis of data"""
    data_type: str  # "stock", "news", "mixed"
    data: dict
    analysis_type: str = "summary"  # "summary", "detailed", "investment_advice"
    user_query: Optional[str] = None


# ============== Stock Data with Embedded AI ==============

@router.post("/stocks/query")
async def embedded_stock_query(
    request: StockQueryRequest,
    x_client_id: Optional[str] = Header(None)
):
    """
    Get stock data with optional AI-powered summary.

    This endpoint is designed for embedded AI usage:
    - Returns structured stock data
    - Optionally includes AI-generated summary
    - Logs usage as EMBEDDED Claude usage

    Use this when your application wants to use our embedded Claude
    responses rather than calling your own LLM.

    Example use case:
    - Third-party app queries: "What are the top tech stocks doing?"
    - This endpoint returns stock data + AI summary
    - Third-party displays the AI summary directly
    """
    logger.info(f"Embedded AI stock query from client: {x_client_id}")

    # Fetch stock data
    try:
        stock_result = await stock_monitor_agent.execute(
            category=request.category,
            symbols=request.symbols,
            format_for_claude=False  # We'll format it ourselves
        )

        response = {
            "data": stock_result,
            "ai_summary": None,
            "usage_type": "embedded"
        }

        # Add AI summary if requested
        if request.include_ai_summary:
            # Generate AI summary using Claude
            summary_prompt = f"""Analyze the following stock data and provide a concise summary.

Stock Data:
{stock_result}

User Query: {request.query_context or 'General stock market overview'}

Provide:
1. Overall market sentiment
2. Top performers and their gains
3. Worst performers and their losses
4. Brief investment insight (2-3 sentences)
"""

            claude_result = await claude_agent.execute(
                message=summary_prompt,
                task="analyze",
                model=ClaudeModel.SONNET.value,
                max_tokens=500
            )

            response["ai_summary"] = claude_result["response"]

            # Log Claude usage as EMBEDDED
            api_logger.log_claude_usage(
                usage_type=ClaudeUsageType.EMBEDDED,
                model=claude_result["model"],
                tokens=claude_result["usage"]["total_tokens"]
            )

        return response

    except Exception as e:
        logger.error(f"Embedded stock query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks/quick")
async def embedded_quick_stocks(
    symbols: Optional[str] = None,
    include_ai: bool = True,
    x_client_id: Optional[str] = Header(None)
):
    """
    Quick stock check with embedded AI summary.

    Simplified endpoint for getting stock data with AI analysis.
    Default: Top tech stocks with AI summary.

    Usage:
    - /embedded-ai/stocks/quick
    - /embedded-ai/stocks/quick?symbols=AAPL,GOOGL,MSFT
    - /embedded-ai/stocks/quick?symbols=AAPL&include_ai=false
    """
    symbol_list = symbols.split(",") if symbols else None

    request = StockQueryRequest(
        symbols=symbol_list,
        category="top_tech",
        include_ai_summary=include_ai
    )

    return await embedded_stock_query(request, x_client_id)


# ============== News with Embedded AI ==============

@router.post("/news/query")
async def embedded_news_query(
    request: NewsQueryRequest,
    x_client_id: Optional[str] = Header(None)
):
    """
    Get news data with AI-powered summary.

    Returns:
    - News articles/videos
    - AI-generated summary of key topics
    - Sentiment analysis
    - Main themes

    Logs usage as EMBEDDED Claude usage.
    """
    logger.info(f"Embedded AI news query from client: {x_client_id}")

    try:
        # Fetch news data
        news_result = await news_search_agent.execute(
            symbols=request.symbols,
            company_names=request.company_names
        )

        # Generate AI summary
        summary_prompt = f"""Analyze the following news data and provide a comprehensive summary.

News Data:
{news_result}

User Query: {request.query_context or 'General news overview'}

Provide:
1. Main themes and topics (3-5 bullet points)
2. Overall sentiment (positive/negative/neutral)
3. Key takeaways for investors
4. Any urgent or breaking news
"""

        claude_result = await claude_agent.execute(
            message=summary_prompt,
            task="analyze",
            model=ClaudeModel.SONNET.value,
            max_tokens=600
        )

        # Log Claude usage as EMBEDDED
        api_logger.log_claude_usage(
            usage_type=ClaudeUsageType.EMBEDDED,
            model=claude_result["model"],
            tokens=claude_result["usage"]["total_tokens"]
        )

        return {
            "data": news_result,
            "ai_summary": claude_result["response"],
            "usage_type": "embedded"
        }

    except Exception as e:
        logger.error(f"Embedded news query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Combined Analysis ==============

@router.post("/analyze")
async def embedded_ai_analysis(
    request: AIAnalysisRequest,
    x_client_id: Optional[str] = Header(None)
):
    """
    AI-powered analysis of provided data.

    Use this when you have data (stock, news, or mixed) and want
    our embedded Claude to analyze it for you.

    Analysis types:
    - summary: Brief overview
    - detailed: In-depth analysis
    - investment_advice: Investment-focused insights

    Logs usage as EMBEDDED Claude usage.
    """
    logger.info(f"Embedded AI analysis from client: {x_client_id}")

    try:
        # Build analysis prompt based on type
        if request.analysis_type == "summary":
            system_prompt = "You are a financial analyst. Provide a concise summary of the data."
            max_tokens = 400
        elif request.analysis_type == "detailed":
            system_prompt = "You are a senior financial analyst. Provide detailed analysis with specific insights."
            max_tokens = 800
        elif request.analysis_type == "investment_advice":
            system_prompt = "You are an investment advisor. Provide actionable investment insights based on the data."
            max_tokens = 600
        else:
            system_prompt = "You are a helpful financial assistant."
            max_tokens = 500

        prompt = f"""Analyze the following {request.data_type} data:

Data:
{request.data}

User Query: {request.user_query or 'Please analyze this data'}

Provide your analysis based on the request type: {request.analysis_type}
"""

        claude_result = await claude_agent.execute(
            message=prompt,
            task="analyze",
            model=ClaudeModel.SONNET.value,
            system_prompt=system_prompt,
            max_tokens=max_tokens
        )

        # Log Claude usage as EMBEDDED
        api_logger.log_claude_usage(
            usage_type=ClaudeUsageType.EMBEDDED,
            model=claude_result["model"],
            tokens=claude_result["usage"]["total_tokens"]
        )

        return {
            "analysis": claude_result["response"],
            "analysis_type": request.analysis_type,
            "data_type": request.data_type,
            "usage_type": "embedded",
            "model": claude_result["model"],
            "tokens_used": claude_result["usage"]["total_tokens"]
        }

    except Exception as e:
        logger.error(f"Embedded AI analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Info Endpoint ==============

@router.get("/info")
async def embedded_ai_info():
    """
    Get information about embedded AI endpoints.

    Explains:
    - What embedded AI means
    - When to use these endpoints
    - Difference from standard endpoints
    - Usage tracking
    """
    return {
        "description": "Embedded AI Endpoints",
        "purpose": "These endpoints are specifically designed for applications that want to use our embedded Claude AI responses",
        "usage_tracking": {
            "embedded": "Using these endpoints logs usage as EMBEDDED, meaning your app uses our AI responses",
            "external": "Using standard endpoints with your own AI logs as EXTERNAL, meaning you have your own LLM"
        },
        "endpoints": {
            "/embedded-ai/stocks/query": "Get stock data with optional AI summary",
            "/embedded-ai/stocks/quick": "Quick stock check with AI (GET request)",
            "/embedded-ai/news/query": "Get news with AI summary",
            "/embedded-ai/analyze": "Analyze provided data with AI"
        },
        "benefits": [
            "No need to manage your own LLM API keys",
            "Consistent AI responses",
            "Optimized prompts for financial data",
            "Token usage tracking",
            "Cost-effective for small applications"
        ],
        "headers": {
            "X-Client-ID": "Optional header to identify your application in logs"
        }
    }
