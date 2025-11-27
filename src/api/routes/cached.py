"""
Optimized API endpoints for cached stock data.
These endpoints serve pre-cached data instantly without making external API calls.
Perfect for third-party integrations, dashboards, and Claude Artifacts.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timezone

from src.core.cache import get_cache
from src.core.scheduler import get_scheduler
from src.agents.stock_monitor import STOCK_LISTS


router = APIRouter()


@router.get("/stocks", summary="Get all cached stocks", tags=["Cached Data"])
async def get_all_cached_stocks():
    """
    Get all stocks currently in cache.

    This endpoint returns instant results from the cache without making any external API calls.
    Perfect for dashboards and third-party integrations.

    Returns:
        - List of all cached stock data
        - Cache statistics
        - Next refresh time
    """
    cache = get_cache()

    # Get all cached stocks
    stocks_dict = cache.get_all_cached()

    # Convert to list
    stocks_list = list(stocks_dict.values())

    # Sort by symbol
    stocks_list.sort(key=lambda x: x.get("symbol", ""))

    # Get cache stats
    stats = cache.get_cache_stats()

    # Get next refresh time
    scheduler = get_scheduler()
    next_refresh = scheduler.get_next_run_time()

    return {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from_cache": True,
        "count": len(stocks_list),
        "stocks": stocks_list,
        "cache_stats": {
            "total_entries": stats["total_entries"],
            "valid_entries": stats["valid_entries"],
            "ttl_seconds": stats["ttl_seconds"],
            "oldest_entry": stats["oldest_entry"],
            "newest_entry": stats["newest_entry"]
        },
        "next_refresh": next_refresh.isoformat() if next_refresh else None
    }


@router.get("/stocks/{symbol}", summary="Get single cached stock", tags=["Cached Data"])
async def get_cached_stock(symbol: str):
    """
    Get a single stock from cache by symbol.

    Args:
        symbol: Stock ticker symbol (e.g., AAPL, MSFT)

    Returns:
        Cached stock data if found

    Raises:
        404: Stock not found in cache
    """
    cache = get_cache()

    # Get stock from cache
    stock_data = cache.get(symbol)

    if not stock_data:
        raise HTTPException(
            status_code=404,
            detail=f"Stock '{symbol.upper()}' not found in cache. Try /api/v1/cached/lists to see available stocks."
        )

    return {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from_cache": True,
        "stock": stock_data
    }


@router.get("/stocks/batch", summary="Get multiple cached stocks", tags=["Cached Data"])
async def get_cached_stocks_batch(
    symbols: List[str] = Query(..., description="List of stock symbols", example=["AAPL", "MSFT", "GOOGL"])
):
    """
    Get multiple stocks from cache in a single request.

    Query params:
        symbols: Comma-separated list of stock symbols

    Example:
        /api/v1/cached/stocks/batch?symbols=AAPL&symbols=MSFT&symbols=GOOGL

    Returns:
        Dict mapping symbols to their cached data
    """
    cache = get_cache()

    # Get stocks from cache
    stocks_dict = cache.get_many(symbols)

    # Find which symbols were not found
    missing = [s for s in symbols if s.upper() not in stocks_dict]

    return {
        "status": "success" if not missing else "partial",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from_cache": True,
        "requested": len(symbols),
        "found": len(stocks_dict),
        "missing": missing if missing else None,
        "stocks": stocks_dict
    }


@router.get("/lists", summary="Get available stock lists", tags=["Cached Data"])
async def get_available_lists():
    """
    Get all available pre-defined stock lists.

    These are the lists that are automatically cached every 30 minutes.

    Returns:
        Dictionary of available stock lists with their symbols
    """
    return {
        "status": "success",
        "lists": {
            name: {
                "name": data["name"],
                "count": len(data["symbols"]),
                "symbols": data["symbols"]
            }
            for name, data in STOCK_LISTS.items()
        }
    }


@router.get("/lists/{list_name}", summary="Get stocks from a specific list", tags=["Cached Data"])
async def get_cached_list(list_name: str):
    """
    Get all stocks from a specific pre-defined list.

    Args:
        list_name: Name of the list (top_tech, top_sp500, top_diversified)

    Returns:
        All stocks from that list currently in cache

    Raises:
        404: List not found
    """
    if list_name not in STOCK_LISTS:
        raise HTTPException(
            status_code=404,
            detail=f"List '{list_name}' not found. Available lists: {list(STOCK_LISTS.keys())}"
        )

    list_info = STOCK_LISTS[list_name]
    symbols = list_info["symbols"]

    cache = get_cache()
    stocks_dict = cache.get_many(symbols)

    # Convert to list maintaining original order
    stocks_list = [stocks_dict[symbol] for symbol in symbols if symbol in stocks_dict]

    # Sort by change percentage
    stocks_list.sort(key=lambda x: x.get("change_percent", 0), reverse=True)

    # Calculate summary
    if stocks_list:
        avg_change = sum(s.get("change_percent", 0) for s in stocks_list) / len(stocks_list)
        gainers = [s for s in stocks_list if s.get("change_percent", 0) > 0]
        losers = [s for s in stocks_list if s.get("change_percent", 0) < 0]
    else:
        avg_change = 0
        gainers = []
        losers = []

    return {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from_cache": True,
        "list_name": list_info["name"],
        "summary": {
            "total_stocks": len(symbols),
            "cached_stocks": len(stocks_list),
            "gainers": len(gainers),
            "losers": len(losers),
            "unchanged": len(stocks_list) - len(gainers) - len(losers),
            "average_change_percent": round(avg_change, 2)
        },
        "top_gainers": stocks_list[:3] if len(stocks_list) >= 3 else stocks_list,
        "top_losers": stocks_list[-3:][::-1] if len(stocks_list) >= 3 else [],
        "stocks": stocks_list
    }


@router.get("/stats", summary="Get cache statistics", tags=["Cached Data"])
async def get_cache_stats():
    """
    Get detailed cache statistics.

    Returns:
        - Number of cached entries
        - Cache age information
        - Next refresh time
        - Scheduler status
    """
    cache = get_cache()
    scheduler = get_scheduler()

    stats = cache.get_cache_stats()
    next_refresh = scheduler.get_next_run_time()
    jobs = scheduler.get_jobs()

    return {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cache": {
            "total_entries": stats["total_entries"],
            "valid_entries": stats["valid_entries"],
            "expired_entries": stats["expired_entries"],
            "ttl_seconds": stats["ttl_seconds"],
            "ttl_minutes": stats["ttl_seconds"] // 60,
            "oldest_entry": stats["oldest_entry"],
            "newest_entry": stats["newest_entry"],
            "db_path": stats["db_path"]
        },
        "scheduler": {
            "is_running": len(jobs) > 0,
            "jobs_count": len(jobs),
            "next_refresh": next_refresh.isoformat() if next_refresh else None
        }
    }


@router.post("/refresh", summary="Trigger manual cache refresh", tags=["Cached Data"])
async def trigger_cache_refresh():
    """
    Manually trigger a cache refresh.

    This will schedule an immediate cache refresh job.
    Useful for testing or forcing a refresh before the scheduled time.

    Returns:
        Status message
    """
    # Import here to avoid circular dependency
    from src.core.scheduler import get_scheduler
    import asyncio

    scheduler = get_scheduler()

    # Trigger a refresh by running the job
    job = scheduler.scheduler.get_job("refresh_stock_cache")

    if not job:
        raise HTTPException(
            status_code=500,
            detail="Cache refresh job not found. Is the scheduler running?"
        )

    # Modify the job to run immediately
    job.modify(next_run_time=datetime.now(timezone.utc))

    return {
        "status": "success",
        "message": "Cache refresh triggered",
        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
    }


@router.delete("/cache", summary="Clear all cached data", tags=["Cached Data"])
async def clear_cache():
    """
    Clear all cached stock data.

    This will remove all entries from the cache.
    The next scheduled refresh will repopulate it.

    Returns:
        Status message
    """
    cache = get_cache()
    cache.clear()

    return {
        "status": "success",
        "message": "Cache cleared successfully",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
