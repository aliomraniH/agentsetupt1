"""
Stock Monitor Agent - Fetches top stock information
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from enum import Enum
import asyncio
import time
from loguru import logger

try:
    import yfinance as yf
except ImportError:
    yf = None

from src.agents.base import BaseAgent


class StockCategory(str, Enum):
    """Categories of stocks to fetch"""
    TOP_TECH = "top_tech"
    TOP_SP500 = "top_sp500"
    TOP_GAINERS = "top_gainers"
    CUSTOM = "custom"


# Pre-defined stock lists
STOCK_LISTS = {
    "top_tech": {
        "name": "Top Tech Stocks",
        "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "INTC", "CRM"]
    },
    "top_sp500": {
        "name": "Top S&P 500 by Market Cap",
        "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "BRK-B", "META", "UNH", "XOM", "JNJ"]
    },
    "top_diversified": {
        "name": "Top Diversified Portfolio",
        "symbols": ["AAPL", "MSFT", "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "PFE"]
    }
}


class StockMonitorAgent(BaseAgent):
    """
    Agent for monitoring stock market information.

    Fetches real-time stock data including:
    - Current price
    - Daily change (absolute and percentage)
    - Volume
    - Market cap
    - 52-week high/low

    Can be triggered via API for use with Claude Chat or other services.
    """

    def __init__(self):
        super().__init__()
        self._cache: Dict[str, Any] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = 300  # 5 minutes cache

    @property
    def name(self) -> str:
        return "stock-monitor"

    @property
    def description(self) -> str:
        return "Monitors top stocks and provides real-time market data"

    def _format_large_number(self, num: float) -> str:
        """Format large numbers for readability"""
        if num is None:
            return "N/A"
        if num >= 1e12:
            return f"${num/1e12:.2f}T"
        if num >= 1e9:
            return f"${num/1e9:.2f}B"
        if num >= 1e6:
            return f"${num/1e6:.2f}M"
        return f"${num:,.0f}"

    def _format_volume(self, vol: float) -> str:
        """Format volume numbers"""
        if vol is None:
            return "N/A"
        if vol >= 1e9:
            return f"{vol/1e9:.2f}B"
        if vol >= 1e6:
            return f"{vol/1e6:.2f}M"
        if vol >= 1e3:
            return f"{vol/1e3:.1f}K"
        return f"{vol:,.0f}"

    def _is_cache_valid(self, symbols_key: str) -> bool:
        """Check if cache is still valid"""
        if not self._cache_time or symbols_key not in self._cache:
            return False
        elapsed = (datetime.now(timezone.utc) - self._cache_time).total_seconds()
        return elapsed < self._cache_ttl

    async def _fetch_batch_data(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Fetch data for multiple stocks using batch download.
        This is more efficient and less likely to be rate limited.

        Args:
            symbols: List of stock ticker symbols

        Returns:
            Dict with stock information for each symbol
        """
        if yf is None:
            return {symbol: {"symbol": symbol, "error": "yfinance not installed", "status": "error"}
                    for symbol in symbols}

        results = {}

        try:
            # Use batch download - more efficient and less rate limiting
            loop = asyncio.get_event_loop()

            # Download historical data for all symbols at once
            symbols_str = " ".join(symbols)

            def download_data():
                return yf.download(
                    symbols_str,
                    period="2d",  # Get 2 days for previous close calculation
                    interval="1d",
                    group_by="ticker",
                    auto_adjust=True,
                    progress=False,
                    threads=False  # Single thread to avoid rate limits
                )

            data = await loop.run_in_executor(None, download_data)

            # Process each symbol
            for symbol in symbols:
                try:
                    if len(symbols) == 1:
                        # Single stock - data structure is different
                        symbol_data = data
                    else:
                        symbol_data = data[symbol] if symbol in data.columns.get_level_values(0) else None

                    if symbol_data is None or symbol_data.empty:
                        results[symbol] = {
                            "symbol": symbol,
                            "error": "No data available",
                            "status": "error"
                        }
                        continue

                    # Get latest and previous close
                    if len(symbol_data) >= 2:
                        current_price = float(symbol_data['Close'].iloc[-1])
                        previous_close = float(symbol_data['Close'].iloc[-2])
                    elif len(symbol_data) == 1:
                        current_price = float(symbol_data['Close'].iloc[-1])
                        previous_close = float(symbol_data['Open'].iloc[-1])
                    else:
                        results[symbol] = {
                            "symbol": symbol,
                            "error": "Insufficient data",
                            "status": "error"
                        }
                        continue

                    # Calculate change
                    change = current_price - previous_close
                    change_percent = (change / previous_close) * 100 if previous_close else 0

                    # Get volume
                    volume = float(symbol_data['Volume'].iloc[-1]) if 'Volume' in symbol_data.columns else None

                    results[symbol] = {
                        "symbol": symbol,
                        "name": symbol,  # Batch download doesn't include name
                        "current_price": round(current_price, 2),
                        "previous_close": round(previous_close, 2),
                        "change": round(change, 2),
                        "change_percent": round(change_percent, 2),
                        "volume": int(volume) if volume else None,
                        "volume_formatted": self._format_volume(volume),
                        "high": round(float(symbol_data['High'].iloc[-1]), 2) if 'High' in symbol_data.columns else None,
                        "low": round(float(symbol_data['Low'].iloc[-1]), 2) if 'Low' in symbol_data.columns else None,
                        "open": round(float(symbol_data['Open'].iloc[-1]), 2) if 'Open' in symbol_data.columns else None,
                        "status": "success"
                    }

                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
                    results[symbol] = {
                        "symbol": symbol,
                        "error": str(e),
                        "status": "error"
                    }

            return results

        except Exception as e:
            logger.error(f"Batch download error: {e}")
            # Return error for all symbols
            return {symbol: {"symbol": symbol, "error": str(e), "status": "error"}
                    for symbol in symbols}

    def get_available_lists(self) -> Dict[str, Any]:
        """Get available pre-defined stock lists"""
        return {
            name: {
                "name": data["name"],
                "count": len(data["symbols"]),
                "symbols": data["symbols"]
            }
            for name, data in STOCK_LISTS.items()
        }

    async def run(
        self,
        category: str = "top_tech",
        symbols: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch stock data for specified category or custom symbols.

        Args:
            category: Pre-defined category (top_tech, top_sp500, top_diversified)
            symbols: Custom list of stock symbols (overrides category)

        Returns:
            Dict containing stock data for all requested symbols
        """
        # Determine which symbols to fetch
        if symbols:
            stock_symbols = symbols[:20]  # Limit to 20 stocks
            list_name = "Custom List"
        elif category in STOCK_LISTS:
            stock_symbols = STOCK_LISTS[category]["symbols"]
            list_name = STOCK_LISTS[category]["name"]
        else:
            # Default to top tech
            stock_symbols = STOCK_LISTS["top_tech"]["symbols"]
            list_name = STOCK_LISTS["top_tech"]["name"]

        # Create cache key
        cache_key = ",".join(sorted(stock_symbols))

        # Check cache
        if self._is_cache_valid(cache_key):
            logger.info(f"[{self.name}] Returning cached data for {list_name}")
            return self._cache[cache_key]

        logger.info(f"[{self.name}] Fetching {len(stock_symbols)} stocks: {list_name}")

        # Fetch all stocks using batch download
        results_dict = await self._fetch_batch_data(stock_symbols)
        results = [results_dict[symbol] for symbol in stock_symbols]

        # Sort by market cap (descending)
        successful = [r for r in results if r.get("status") == "success"]
        failed = [r for r in results if r.get("status") == "error"]

        # Sort by change percentage for gainers/losers view
        sorted_by_change = sorted(
            successful,
            key=lambda x: x.get("change_percent", 0),
            reverse=True
        )

        # Calculate summary
        avg_change = (
            sum(s.get("change_percent", 0) for s in successful) / len(successful)
            if successful else 0
        )

        gainers = [s for s in successful if s.get("change_percent", 0) > 0]
        losers = [s for s in successful if s.get("change_percent", 0) < 0]

        result = {
            "list_name": list_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_stocks": len(stock_symbols),
                "successful": len(successful),
                "failed": len(failed),
                "gainers": len(gainers),
                "losers": len(losers),
                "unchanged": len(successful) - len(gainers) - len(losers),
                "average_change_percent": round(avg_change, 2)
            },
            "top_gainers": sorted_by_change[:3] if len(sorted_by_change) >= 3 else sorted_by_change,
            "top_losers": sorted_by_change[-3:][::-1] if len(sorted_by_change) >= 3 else [],
            "stocks": sorted_by_change,
            "errors": failed if failed else None
        }

        # Cache the result
        self._cache[cache_key] = result
        self._cache_time = datetime.now(timezone.utc)

        return result


# Singleton instance
stock_monitor_agent = StockMonitorAgent()
