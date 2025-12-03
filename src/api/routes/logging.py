"""
API routes for logging and monitoring
"""

from fastapi import APIRouter, Query
from typing import Optional
from src.core.api_logger import api_logger

router = APIRouter()


@router.get("/stats")
async def get_api_stats(
    last_n: int = Query(100, description="Number of recent requests to analyze", ge=1, le=1000)
):
    """
    Get comprehensive API usage statistics.

    Shows:
    - Request counts by source (web app, mobile app, third-party, etc.)
    - Request counts by API type (stock price, news, Claude AI, etc.)
    - External API usage (Alpha Vantage, Perplexity, yfinance, etc.)
    - Claude AI usage patterns (embedded vs external)
    - Success rates and performance metrics

    This helps understand:
    - Which clients are using which APIs
    - How third-party apps interact with the service
    - Whether they use embedded Claude or their own AI
    - API call sequences and patterns
    """
    return api_logger.get_request_stats(last_n=last_n)


@router.get("/recent")
async def get_recent_requests(
    last_n: int = Query(20, description="Number of recent requests to retrieve", ge=1, le=100)
):
    """
    Get detailed logs of recent API requests.

    Each log entry includes:
    - Request details (method, path, source)
    - External API calls made
    - Claude AI usage (if applicable)
    - Timing and performance data
    - Success/failure status
    """
    return {
        "count": last_n,
        "requests": api_logger.get_recent_requests(last_n=last_n)
    }


@router.get("/requests/{request_id}")
async def get_request_by_id(request_id: str):
    """
    Get detailed information about a specific request by ID.

    Useful for:
    - Debugging specific API calls
    - Understanding API call chains
    - Tracing issues through the system
    """
    request_data = api_logger.get_request_by_id(request_id)
    if not request_data:
        return {
            "error": "Request not found",
            "request_id": request_id,
            "message": "This request ID was not found in the recent logs"
        }
    return request_data


@router.get("/sources")
async def get_source_breakdown(
    last_n: int = Query(100, description="Number of recent requests to analyze", ge=1, le=1000)
):
    """
    Get a breakdown of API usage by source.

    Helps answer:
    - How many requests come from third-party apps vs web apps?
    - Which clients are the most active?
    - Are embedded AI agents being used?
    """
    stats = api_logger.get_request_stats(last_n=last_n)
    return {
        "total_requests": stats["total_requests"],
        "by_source": stats["requests_by_source"],
        "time_range": stats["time_range"]
    }


@router.get("/external-apis")
async def get_external_api_usage(
    last_n: int = Query(100, description="Number of recent requests to analyze", ge=1, le=1000)
):
    """
    Get statistics on external API usage.

    Shows:
    - Which external APIs are being called (Alpha Vantage, Perplexity, etc.)
    - Success/failure rates for each API
    - Average response times
    - Total call counts

    Helps understand:
    - API reliability
    - Performance bottlenecks
    - Cost tracking (for paid APIs)
    """
    stats = api_logger.get_request_stats(last_n=last_n)
    return {
        "total_requests_analyzed": stats["total_requests"],
        "external_api_usage": stats["external_api_usage"],
        "time_range": stats["time_range"]
    }


@router.get("/claude-usage")
async def get_claude_usage_stats(
    last_n: int = Query(100, description="Number of recent requests to analyze", ge=1, le=1000)
):
    """
    Get Claude AI usage statistics.

    Shows:
    - Embedded usage: Requests using our embedded Claude agent
    - External usage: Third-party apps using their own AI
    - Passthrough usage: Requests passed to our Claude agent by third parties
    - Total tokens consumed

    Helps answer:
    - Are third-party apps using our embedded Claude responses?
    - Or are they calling with their own AI agents?
    - What is the token usage breakdown?
    """
    stats = api_logger.get_request_stats(last_n=last_n)
    return {
        "total_requests_analyzed": stats["total_requests"],
        "claude_usage": stats["claude_usage"],
        "time_range": stats["time_range"],
        "usage_breakdown": {
            "embedded": {
                "count": stats["claude_usage"]["embedded_usage"],
                "percentage": round(
                    (stats["claude_usage"]["embedded_usage"] / stats["claude_usage"]["total_claude_requests"] * 100)
                    if stats["claude_usage"]["total_claude_requests"] > 0 else 0,
                    2
                )
            },
            "external": {
                "count": stats["claude_usage"]["external_usage"],
                "percentage": round(
                    (stats["claude_usage"]["external_usage"] / stats["claude_usage"]["total_claude_requests"] * 100)
                    if stats["claude_usage"]["total_claude_requests"] > 0 else 0,
                    2
                )
            },
            "passthrough": {
                "count": stats["claude_usage"]["passthrough_usage"],
                "percentage": round(
                    (stats["claude_usage"]["passthrough_usage"] / stats["claude_usage"]["total_claude_requests"] * 100)
                    if stats["claude_usage"]["total_claude_requests"] > 0 else 0,
                    2
                )
            }
        }
    }


@router.get("/api-sequences")
async def get_api_call_sequences(
    last_n: int = Query(20, description="Number of recent requests to retrieve", ge=1, le=100)
):
    """
    Get API call sequences to understand how requests flow through the system.

    Shows:
    - Main API endpoint called
    - External APIs called in sequence
    - Timing for each step
    - Success/failure at each stage

    Helps answer:
    - What is the typical sequence for retrieving stock prices?
    - Which fallback APIs are used when primary APIs fail?
    - Where are the bottlenecks in the API call chain?
    """
    requests = api_logger.get_recent_requests(last_n=last_n)

    sequences = []
    for req in requests:
        sequence = {
            "request_id": req["request_id"],
            "timestamp": req["start_time"],
            "source": req["source_type"],
            "main_endpoint": req["path"],
            "duration_ms": req["duration_ms"],
            "success": req["success"],
            "external_api_sequence": [
                {
                    "api": call["api_name"],
                    "endpoint": call["endpoint"],
                    "duration_ms": call["duration_ms"],
                    "success": call["success"]
                }
                for call in req["external_api_calls"]
            ]
        }
        sequences.append(sequence)

    return {
        "count": len(sequences),
        "sequences": sequences
    }
