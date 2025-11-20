"""
Stock Monitor Agent - Fetches top stock information
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum
import asyncio
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

    async def _fetch_stock_data(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch data for a single stock.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dict with stock information
        """
        if yf is None:
            return {
                "symbol": symbol,
                "error": "yfinance not installed"
            }

        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol)

            # Get current info
            info = await loop.run_in_executor(None, lambda: ticker.info)

            # Extract relevant data
            current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            previous_close = info.get('previousClose', 0)

            if current_price and previous_close:
                change = current_price - previous_close
                change_percent = (change / previous_close) * 100
            else:
                change = 0
                change_percent = 0

            return {
                "symbol": symbol,
                "name": info.get('shortName', info.get('longName', symbol)),
                "current_price": round(current_price, 2) if current_price else None,
                "previous_close": round(previous_close, 2) if previous_close else None,
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "volume": info.get('volume'),
                "volume_formatted": self._format_volume(info.get('volume')),
                "market_cap": info.get('marketCap'),
                "market_cap_formatted": self._format_large_number(info.get('marketCap')),
                "fifty_two_week_high": info.get('fiftyTwoWeekHigh'),
                "fifty_two_week_low": info.get('fiftyTwoWeekLow'),
                "pe_ratio": round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else None,
                "dividend_yield": round(info.get('dividendYield', 0) * 100, 2) if info.get('dividendYield') else None,
                "sector": info.get('sector', 'N/A'),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return {
                "symbol": symbol,
                "error": str(e),
                "status": "error"
            }

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

        logger.info(f"[{self.name}] Fetching {len(stock_symbols)} stocks: {list_name}")

        # Fetch all stocks concurrently
        tasks = [self._fetch_stock_data(symbol) for symbol in stock_symbols]
        results = await asyncio.gather(*tasks)

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
        total_market_cap = sum(s.get("market_cap", 0) or 0 for s in successful)
        avg_change = (
            sum(s.get("change_percent", 0) for s in successful) / len(successful)
            if successful else 0
        )

        gainers = [s for s in successful if s.get("change_percent", 0) > 0]
        losers = [s for s in successful if s.get("change_percent", 0) < 0]

        return {
            "list_name": list_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_stocks": len(stock_symbols),
                "successful": len(successful),
                "failed": len(failed),
                "gainers": len(gainers),
                "losers": len(losers),
                "unchanged": len(successful) - len(gainers) - len(losers),
                "average_change_percent": round(avg_change, 2),
                "total_market_cap": self._format_large_number(total_market_cap)
            },
            "top_gainers": sorted_by_change[:3] if len(sorted_by_change) >= 3 else sorted_by_change,
            "top_losers": sorted_by_change[-3:][::-1] if len(sorted_by_change) >= 3 else [],
            "stocks": sorted_by_change,
            "errors": failed if failed else None
        }


# Singleton instance
stock_monitor_agent = StockMonitorAgent()
