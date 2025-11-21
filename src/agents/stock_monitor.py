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
    import pandas as pd
except ImportError:
    yf = None
    pd = None

try:
    import httpx
    from bs4 import BeautifulSoup
except ImportError:
    httpx = None
    BeautifulSoup = None

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from src.agents.base import BaseAgent
from src.core.config import settings


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

    async def _fetch_with_llm_search(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Fetch stock data using LLM-powered search (Perplexity).
        More reliable than web scraping as LLM can understand and extract data from various sources.
        """
        if AsyncOpenAI is None or not settings.perplexity_api_key:
            logger.warning("Perplexity API not configured - skipping LLM search")
            return {symbol: {"symbol": symbol, "error": "Perplexity API not configured", "status": "error"}
                    for symbol in symbols}

        results = {}

        # Initialize Perplexity client (uses OpenAI-compatible API)
        client = AsyncOpenAI(
            api_key=settings.perplexity_api_key,
            base_url="https://api.perplexity.ai"
        )

        for symbol in symbols:
            try:
                # Craft a precise prompt for stock data
                prompt = f"""Get the latest stock data for {symbol}. Return ONLY a JSON object with this exact structure (no markdown, no explanation):
{{
  "symbol": "{symbol}",
  "current_price": <latest price as number>,
  "previous_close": <previous day close as number>,
  "change": <price change as number>,
  "change_percent": <percent change as number>,
  "volume": <trading volume as integer>,
  "company_name": "<full company name>"
}}

Requirements:
- All prices must be in USD
- Use the most recent trading data available
- Return only valid JSON, no additional text
- Ensure all numeric fields are actual numbers, not strings"""

                response = await client.chat.completions.create(
                    model="llama-3.1-sonar-small-128k-online",  # Perplexity's fast search model
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a financial data extraction assistant. Return only valid JSON with stock data, no explanations or markdown."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.0,  # Deterministic output
                    max_tokens=500
                )

                # Parse LLM response
                content = response.choices[0].message.content.strip()

                # Remove markdown code blocks if present
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                content = content.strip()

                # Parse JSON
                import json
                data = json.loads(content)

                # Validate and format response
                current_price = float(data.get("current_price", 0))
                previous_close = float(data.get("previous_close", 0))
                change = float(data.get("change", 0))
                change_percent = float(data.get("change_percent", 0))
                volume = int(data.get("volume", 0)) if data.get("volume") else None

                # Recalculate if needed
                if not change and current_price and previous_close:
                    change = current_price - previous_close
                if not change_percent and current_price and previous_close:
                    change_percent = (change / previous_close) * 100

                results[symbol] = {
                    "symbol": symbol,
                    "name": data.get("company_name", symbol),
                    "current_price": round(current_price, 2),
                    "previous_close": round(previous_close, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_percent, 2),
                    "volume": volume,
                    "volume_formatted": self._format_volume(volume) if volume else "N/A",
                    "status": "success"
                }
                logger.info(f"Successfully fetched {symbol} via LLM search")

            except json.JSONDecodeError as e:
                logger.error(f"LLM returned invalid JSON for {symbol}: {content[:200]}")
                results[symbol] = {
                    "symbol": symbol,
                    "error": f"LLM JSON parse error: {str(e)}",
                    "status": "error"
                }
            except Exception as e:
                logger.error(f"LLM search error for {symbol}: {e}")
                results[symbol] = {
                    "symbol": symbol,
                    "error": f"LLM search error: {str(e)}",
                    "status": "error"
                }

        return results

    async def _scrape_yahoo_finance(self, symbol: str) -> Dict[str, Any]:
        """
        Scrape stock data from Yahoo Finance website.
        More reliable than yfinance API.
        """
        if httpx is None or BeautifulSoup is None:
            return {"symbol": symbol, "error": "httpx or BeautifulSoup not installed", "status": "error"}

        try:
            url = f"https://finance.yahoo.com/quote/{symbol}"
            
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    return {"symbol": symbol, "error": f"HTTP {response.status_code}", "status": "error"}

                soup = BeautifulSoup(response.text, 'lxml')

                # Method 1: Try to extract from embedded JSON (most reliable)
                current_price = None
                change = None
                change_percent = None
                previous_close = None
                volume = None

                # Look for script tags containing JSON data
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and 'root.App.main' in script.string:
                        try:
                            # Extract JSON from the script
                            import json
                            import re

                            # Find the JSON object
                            match = re.search(r'root\.App\.main\s*=\s*({.*?});', script.string, re.DOTALL)
                            if match:
                                data = json.loads(match.group(1))

                                # Navigate to quote data
                                if 'context' in data and 'dispatcher' in data['context']:
                                    stores = data['context']['dispatcher']['stores']
                                    if 'QuoteSummaryStore' in stores:
                                        quote_data = stores['QuoteSummaryStore']

                                        # Extract price data
                                        if 'price' in quote_data:
                                            price_info = quote_data['price']
                                            current_price = price_info.get('regularMarketPrice', {}).get('raw')
                                            change = price_info.get('regularMarketChange', {}).get('raw')
                                            change_percent = price_info.get('regularMarketChangePercent', {}).get('raw')
                                            previous_close = price_info.get('regularMarketPreviousClose', {}).get('raw')
                                            volume = price_info.get('regularMarketVolume', {}).get('raw')

                                        break
                        except Exception as e:
                            logger.debug(f"Failed to parse JSON for {symbol}: {e}")
                            continue

                # Method 2: Extract current price from HTML - try multiple selectors
                if not current_price:
                    # Try fin-streamer with data-symbol
                    price_element = soup.find('fin-streamer', {'data-symbol': symbol, 'data-field': 'regularMarketPrice'})
                    if price_element:
                        try:
                            current_price = float(price_element.text.replace(',', ''))
                        except:
                            pass

                    # Try fin-streamer without data-symbol
                    if not current_price:
                        price_element = soup.find('fin-streamer', {'data-field': 'regularMarketPrice'})
                        if price_element:
                            try:
                                current_price = float(price_element.text.replace(',', ''))
                            except:
                                pass

                    # Look for price in specific div/span patterns
                    if not current_price:
                        for tag in soup.find_all(['span', 'div'], class_=lambda x: x and 'price' in x.lower() if x else False):
                            try:
                                text = tag.text.strip().replace(',', '').replace('$', '')
                                if text and text[0].isdigit():
                                    current_price = float(text)
                                    break
                            except:
                                continue

                # Extract change from HTML if not from JSON
                if change is None:
                    change_element = soup.find('fin-streamer', {'data-field': 'regularMarketChange'})
                    if change_element:
                        try:
                            change = float(change_element.text.replace(',', ''))
                        except:
                            pass

                # Extract change percent from HTML if not from JSON
                if change_percent is None:
                    change_pct_element = soup.find('fin-streamer', {'data-field': 'regularMarketChangePercent'})
                    if change_pct_element:
                        try:
                            change_pct_text = change_pct_element.text.replace('%', '').replace('(', '').replace(')', '')
                            change_percent = float(change_pct_text)
                        except:
                            pass

                # Extract previous close from HTML if not from JSON
                if previous_close is None:
                    prev_close_element = soup.find('td', {'data-test': 'PREV_CLOSE-value'})
                    if prev_close_element:
                        try:
                            previous_close = float(prev_close_element.text.replace(',', ''))
                        except:
                            pass

                # Extract volume from HTML if not from JSON
                if volume is None:
                    volume_element = soup.find('fin-streamer', {'data-field': 'regularMarketVolume'})
                    if volume_element:
                        try:
                            volume_text = volume_element.text.replace(',', '')
                            volume = int(volume_text) if volume_text else None
                        except:
                            pass

                # Calculate missing values
                if current_price and previous_close and change is None:
                    change = current_price - previous_close
                if current_price and previous_close and change_percent is None:
                    change_percent = (change / previous_close) * 100
                if previous_close is None and current_price and change:
                    previous_close = current_price - change
                elif change_percent and current_price and not previous_close:
                    # Calculate previous close from percent change
                    previous_close = current_price / (1 + change_percent/100)

                # Normalize prices - detect if prices are in wrong units
                # Most major stocks trade between $10 and $1000. Outside this range needs validation.
                if current_price:
                    # If price > 2000, likely in cents (need to divide by 100)
                    if current_price > 2000:
                        if change_percent and abs(change_percent) < 20:  # Reasonable daily change
                            current_price = current_price / 100
                            if previous_close:
                                previous_close = previous_close / 100
                            if change:
                                change = change / 100

                    # If price is very low (< $5) for major tech stocks, might be missing a multiplier
                    # But be careful - some stocks legitimately trade below $5
                    # For now, we'll just log this for debugging
                    if current_price < 10:
                        logger.debug(f"{symbol} price seems low: ${current_price}")

                # Recalculate if we normalized
                if current_price and previous_close:
                    change = current_price - previous_close
                    change_percent = (change / previous_close) * 100

                # Validation: Check if the data seems reasonable
                if current_price:
                    # If change_percent is extremely high but absolute change is tiny, data is suspect
                    if change_percent and abs(change_percent) > 50 and change and abs(change) < 1:
                        logger.warning(f"{symbol} suspicious data: {change_percent}% change but only ${change}")
                        return {"symbol": symbol, "error": "Suspicious price data detected", "status": "error"}

                return {
                    "symbol": symbol,
                    "name": symbol,
                    "current_price": round(current_price, 2) if current_price else None,
                    "previous_close": round(previous_close, 2) if previous_close else None,
                    "change": round(change, 2) if change else 0,
                    "change_percent": round(change_percent, 2) if change_percent else 0,
                    "volume": volume,
                    "volume_formatted": self._format_volume(volume),
                    "status": "success"
                }

        except Exception as e:
            logger.error(f"Error scraping {symbol}: {e}")
            return {"symbol": symbol, "error": str(e), "status": "error"}

    async def _fetch_stocks_web_scraping(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Fetch stock data using web scraping.
        Fallback when yfinance fails.
        """
        logger.info(f"Fetching {len(symbols)} stocks via web scraping")
        
        # Scrape each stock with delay to avoid rate limiting
        results = {}
        for i, symbol in enumerate(symbols):
            result = await self._scrape_yahoo_finance(symbol)
            results[symbol] = result
            
            # Add small delay between requests to be polite
            if i < len(symbols) - 1:
                await asyncio.sleep(0.5)
        
        return results




    async def _fetch_ticker_info(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Fetch stock data using yfinance Ticker().history() method.
        This works even when markets are closed by getting historical data.
        """
        if yf is None:
            return {symbol: {"symbol": symbol, "error": "yfinance not installed", "status": "error"}
                    for symbol in symbols}

        results = {}
        loop = asyncio.get_event_loop()

        for symbol in symbols:
            try:
                def get_ticker_history():
                    ticker = yf.Ticker(symbol)
                    # Get last 2 days of history to ensure we have recent data
                    hist = ticker.history(period="2d")
                    info = ticker.info
                    return hist, info

                hist, info = await loop.run_in_executor(None, get_ticker_history)

                if hist.empty or len(hist) == 0:
                    results[symbol] = {
                        "symbol": symbol,
                        "error": "No historical data available",
                        "status": "error"
                    }
                    continue

                # Get the most recent day's data
                latest = hist.iloc[-1]
                current_price = float(latest['Close'])

                # Get previous close
                if len(hist) >= 2:
                    previous_close = float(hist.iloc[-2]['Close'])
                else:
                    previous_close = float(latest['Open'])

                change = current_price - previous_close
                change_percent = (change / previous_close) * 100 if previous_close else 0
                volume = int(latest['Volume']) if 'Volume' in latest else None

                results[symbol] = {
                    "symbol": symbol,
                    "name": info.get('longName') or info.get('shortName') or symbol,
                    "current_price": round(current_price, 2),
                    "previous_close": round(previous_close, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_percent, 2),
                    "volume": volume,
                    "volume_formatted": self._format_volume(volume) if volume else "N/A",
                    "status": "success"
                }
                logger.info(f"Successfully fetched {symbol} via Ticker history")

            except Exception as e:
                logger.error(f"Ticker history error for {symbol}: {e}")
                results[symbol] = {
                    "symbol": symbol,
                    "error": f"Ticker history error: {str(e)}",
                    "status": "error"
                }

        return results

    async def _fetch_batch_data(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Fetch data for multiple stocks using batch download.
        This is more efficient and less likely to be rate limited.
        """
        if yf is None:
            return {symbol: {"symbol": symbol, "error": "yfinance not installed", "status": "error"}
                    for symbol in symbols}

        results = {}

        try:
            loop = asyncio.get_event_loop()
            symbols_str = " ".join(symbols)

            def download_data():
                # Use download with specific parameters to avoid rate limits
                # Use longer period to ensure we get data even when markets are closed
                data = yf.download(
                    symbols_str,
                    period="2d",  # Get last 2 days to ensure we have recent data
                    interval="1d",
                    group_by="ticker",
                    auto_adjust=True,
                    progress=False,
                    threads=False,
                    prepost=True  # Include pre/post market data
                )
                return data

            data = await loop.run_in_executor(None, download_data)

            if data is None or data.empty:
                logger.error("yfinance returned empty data - all stocks failed")
                # Return errors instead of demo data so web scraping can be tried
                return {symbol: {"symbol": symbol, "error": "yfinance returned empty data", "status": "error"}
                        for symbol in symbols}

            # Process each symbol
            for symbol in symbols:
                try:
                    # Handle single vs multiple symbols (different data structure)
                    if len(symbols) == 1:
                        symbol_data = data
                    else:
                        if symbol not in data.columns.get_level_values(0):
                            results[symbol] = {
                                "symbol": symbol,
                                "error": "Symbol not found",
                                "status": "error"
                            }
                            continue
                        symbol_data = data[symbol]

                    if symbol_data.empty:
                        results[symbol] = {
                            "symbol": symbol,
                            "error": "No data available",
                            "status": "error"
                        }
                        continue

                    # Get latest data
                    latest = symbol_data.iloc[-1]

                    # Get previous close (second to last row)
                    if len(symbol_data) >= 2:
                        previous_close = float(symbol_data['Close'].iloc[-2])
                    else:
                        previous_close = float(latest['Open'])

                    current_price = float(latest['Close'])
                    change = current_price - previous_close
                    change_percent = (change / previous_close) * 100 if previous_close else 0
                    volume = float(latest['Volume']) if 'Volume' in latest else None

                    results[symbol] = {
                        "symbol": symbol,
                        "name": symbol,
                        "current_price": round(current_price, 2),
                        "previous_close": round(previous_close, 2),
                        "change": round(change, 2),
                        "change_percent": round(change_percent, 2),
                        "volume": int(volume) if volume else None,
                        "volume_formatted": self._format_volume(volume),
                        "high": round(float(latest['High']), 2) if 'High' in latest else None,
                        "low": round(float(latest['Low']), 2) if 'Low' in latest else None,
                        "open": round(float(latest['Open']), 2) if 'Open' in latest else None,
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
            error_msg = str(e)
            logger.error(f"Batch download error: {error_msg}")

            # Return errors instead of demo data - let web scraping be tried as fallback
            logger.warning(f"yfinance failed with exception: {error_msg}")
            return {symbol: {"symbol": symbol, "error": f"yfinance error: {error_msg}", "status": "error"}
                    for symbol in symbols}

    def _get_demo_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Return demo data when rate limited"""
        import random

        demo_prices = {
            "AAPL": 178.50, "MSFT": 378.20, "GOOGL": 141.80, "AMZN": 178.90,
            "NVDA": 495.50, "META": 503.20, "TSLA": 248.50, "AMD": 138.70,
            "INTC": 44.80, "CRM": 273.40, "BRK-B": 363.50, "UNH": 528.90,
            "XOM": 104.20, "JNJ": 156.80, "JPM": 158.90, "V": 259.30,
            "PG": 153.40, "HD": 348.70, "MA": 428.60, "PFE": 28.90
        }

        results = {}
        for symbol in symbols:
            base_price = demo_prices.get(symbol, 100.0)
            change_pct = random.uniform(-3, 3)
            current = base_price * (1 + change_pct/100)

            results[symbol] = {
                "symbol": symbol,
                "name": symbol,
                "current_price": round(current, 2),
                "previous_close": round(base_price, 2),
                "change": round(current - base_price, 2),
                "change_percent": round(change_pct, 2),
                "volume": random.randint(10000000, 100000000),
                "volume_formatted": f"{random.randint(10, 100)}M",
                "high": round(current * 1.01, 2),
                "low": round(current * 0.99, 2),
                "open": round(base_price, 2),
                "status": "success",
                "is_demo": True
            }

        return results

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

    def _format_for_claude(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the result in a Claude-friendly structure.
        This makes it easy for Claude Chat to parse and present.
        """
        stocks = result.get("stocks", [])

        # Create a simple text summary
        summary_text = f"📈 {result['list_name']} - {result['timestamp'][:10]}\n\n"

        if stocks:
            summary_text += "Top Performers:\n"
            for i, stock in enumerate(result.get("top_gainers", [])[:3], 1):
                summary_text += f"{i}. {stock['symbol']}: ${stock['current_price']} ({stock['change_percent']:+.2f}%)\n"

            summary_text += "\nBottom Performers:\n"
            for i, stock in enumerate(result.get("top_losers", [])[:3], 1):
                summary_text += f"{i}. {stock['symbol']}: ${stock['current_price']} ({stock['change_percent']:+.2f}%)\n"

            summary_text += f"\nAverage Change: {result['summary']['average_change_percent']:+.2f}%"
        else:
            summary_text += "No stock data available."

        return {
            "text_summary": summary_text,
            "data": result
        }

    async def run(
        self,
        category: str = "top_tech",
        symbols: Optional[List[str]] = None,
        format_for_claude: bool = True,
        skip_cache: bool = False,
        debug: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch stock data for specified category or custom symbols.

        Args:
            category: Pre-defined category (top_tech, top_sp500, top_diversified)
            symbols: Custom list of stock symbols (overrides category)
            format_for_claude: Include Claude-friendly text summary
            skip_cache: If True, bypass cache and fetch fresh data
            debug: If True, include debug metadata (data sources, validation results)

        Returns:
            Dict containing stock data for all requested symbols
        """
        # Initialize debug metadata
        debug_metadata = {
            "cache_used": False,
            "data_sources": {},
            "validation_warnings": [],
            "fetch_order": []
        } if debug else None

        # Determine which symbols to fetch
        if symbols:
            stock_symbols = [s.upper() for s in symbols[:20]]
            list_name = "Custom List"
        elif category in STOCK_LISTS:
            stock_symbols = STOCK_LISTS[category]["symbols"]
            list_name = STOCK_LISTS[category]["name"]
        else:
            stock_symbols = STOCK_LISTS["top_tech"]["symbols"]
            list_name = STOCK_LISTS["top_tech"]["name"]

        # Create cache key
        cache_key = ",".join(sorted(stock_symbols))

        # Check cache (unless skip_cache is True)
        if not skip_cache and self._is_cache_valid(cache_key):
            logger.info(f"[{self.name}] Returning cached data for {list_name}")
            cached_result = self._cache[cache_key]
            if debug_metadata:
                cached_result["_debug"] = {
                    "cache_used": True,
                    "cache_age_seconds": (datetime.now(timezone.utc) - self._cache_time).total_seconds(),
                    "note": "This is cached data. Use ?skip_cache=true to fetch fresh data."
                }
            return cached_result

        if skip_cache:
            logger.info(f"[{self.name}] Cache bypassed - fetching fresh data for {list_name}")
        else:
            logger.info(f"[{self.name}] Cache miss - fetching {len(stock_symbols)} stocks: {list_name}")

        if debug_metadata:
            debug_metadata["fetch_order"].append("Starting fresh data fetch")

        # Strategy: Try yfinance first (more reliable official API), then web scraping as fallback
        if yf is not None:
            logger.info("Using yfinance as primary data source")
            if debug_metadata:
                debug_metadata["fetch_order"].append("Attempting yfinance for all symbols")
            results_dict = await self._fetch_batch_data(stock_symbols)

            # Track which stocks succeeded with yfinance
            if debug_metadata:
                for symbol, data in results_dict.items():
                    if data.get("status") == "success":
                        debug_metadata["data_sources"][symbol] = "yfinance"
        else:
            logger.warning("yfinance not available, using web scraping only")
            if debug_metadata:
                debug_metadata["fetch_order"].append("yfinance not available - will use web scraping")
            results_dict = {}

        # Check which stocks succeeded/failed with yfinance download
        failed_symbols = [symbol for symbol, data in results_dict.items() if data.get("status") == "error"]

        # Also check for missing symbols
        for symbol in stock_symbols:
            if symbol not in results_dict:
                failed_symbols.append(symbol)

        # If any stocks failed with yfinance download, try Ticker API
        if failed_symbols and yf is not None:
            logger.info(f"Retrying {len(failed_symbols)} failed stocks with yfinance Ticker API: {failed_symbols}")
            if debug_metadata:
                debug_metadata["fetch_order"].append(f"Retrying {len(failed_symbols)} stocks with yfinance Ticker API")
            ticker_results = await self._fetch_ticker_info(failed_symbols)

            # Merge successful Ticker API results
            still_failed = []
            for symbol in failed_symbols:
                if ticker_results[symbol].get("status") == "success":
                    results_dict[symbol] = ticker_results[symbol]
                    logger.info(f"Successfully fetched {symbol} data from Ticker API")
                    if debug_metadata:
                        debug_metadata["data_sources"][symbol] = "yfinance_ticker_api"
                else:
                    still_failed.append(symbol)

            failed_symbols = still_failed

        # If still have failures, try LLM-powered search (Perplexity)
        if failed_symbols and settings.perplexity_api_key:
            logger.info(f"Retrying {len(failed_symbols)} failed stocks with LLM search: {failed_symbols}")
            if debug_metadata:
                debug_metadata["fetch_order"].append(f"Retrying {len(failed_symbols)} stocks with LLM search (Perplexity)")
            llm_results = await self._fetch_with_llm_search(failed_symbols)

            # Merge successful LLM results
            still_failed = []
            for symbol in failed_symbols:
                if llm_results[symbol].get("status") == "success":
                    results_dict[symbol] = llm_results[symbol]
                    logger.info(f"Successfully fetched {symbol} data from LLM search")
                    if debug_metadata:
                        debug_metadata["data_sources"][symbol] = "llm_search"
                else:
                    still_failed.append(symbol)

            failed_symbols = still_failed

        # If still have failures, try web scraping as final fallback
        if failed_symbols:
            logger.info(f"Retrying {len(failed_symbols)} failed stocks with web scraping: {failed_symbols}")
            if debug_metadata:
                debug_metadata["fetch_order"].append(f"Retrying {len(failed_symbols)} stocks with web scraping: {failed_symbols}")
            scraping_results = await self._fetch_stocks_web_scraping(failed_symbols)

            # Merge successful scraping results back
            for symbol in failed_symbols:
                if scraping_results[symbol].get("status") == "success":
                    results_dict[symbol] = scraping_results[symbol]
                    logger.info(f"Successfully fetched {symbol} data from web scraping")
                    if debug_metadata:
                        debug_metadata["data_sources"][symbol] = "web_scraping"
                elif symbol not in results_dict:
                    # Keep the error result
                    results_dict[symbol] = scraping_results[symbol]
                    if debug_metadata:
                        debug_metadata["data_sources"][symbol] = "failed"

        # Final validation: Detect suspicious data patterns
        successful_data = {symbol: data for symbol, data in results_dict.items()
                          if data.get("status") == "success" and data.get("current_price") is not None}

        # Sanity check: Major tech stocks should be within reasonable price ranges
        # This catches obviously wrong data (100x too high/low)
        expected_ranges = {
            "AAPL": (100, 300),    # Apple typically $150-250
            "MSFT": (200, 500),    # Microsoft typically $300-450
            "GOOGL": (80, 200),    # Alphabet typically $120-180
            "AMZN": (100, 250),    # Amazon typically $130-200
            "META": (200, 700),    # Meta typically $300-600
            "TSLA": (150, 500),    # Tesla typically $200-400
            "NVDA": (100, 300),    # Nvidia typically $150-250
            "AMD": (50, 250),      # AMD typically $100-200
            "INTC": (15, 80),      # Intel typically $20-50
            "CRM": (150, 350)      # Salesforce typically $200-300
        }

        for symbol, data in successful_data.items():
            price = data.get("current_price")
            if symbol in expected_ranges and price:
                min_price, max_price = expected_ranges[symbol]
                if price < min_price * 0.5 or price > max_price * 2:
                    warning_msg = f"{symbol}: Price ${price} outside typical range ${min_price}-${max_price}"
                    logger.error(f"Price out of range - {warning_msg}")
                    # Mark as suspicious but keep the data with a warning
                    data["warning"] = f"Price ${price} outside typical range ${min_price}-${max_price}"
                    if debug_metadata:
                        debug_metadata["validation_warnings"].append(warning_msg)

        # Cross-check: detect if multiple stocks have identical prices (data quality issue)
        if len(successful_data) > 1:
            prices = [data["current_price"] for data in successful_data.values()]
            if len(prices) != len(set(prices)):
                price_counts = {}
                for symbol, data in successful_data.items():
                    price = data["current_price"]
                    if price not in price_counts:
                        price_counts[price] = []
                    price_counts[price].append(symbol)

                # Warn about duplicates
                for price, symbols_with_price in price_counts.items():
                    if len(symbols_with_price) > 1:
                        warning_msg = f"DUPLICATE PRICES - ${price}: {symbols_with_price}"
                        logger.error(warning_msg)
                        # Add warning to each affected stock
                        for sym in symbols_with_price:
                            if sym in successful_data:
                                successful_data[sym]["warning"] = f"Duplicate price detected with {symbols_with_price}"
                        if debug_metadata:
                            debug_metadata["validation_warnings"].append(warning_msg)

        # Convert to list maintaining original order
        results = [results_dict[symbol] for symbol in stock_symbols]

        # Final success/failure counts
        successful = [r for r in results if r.get("status") == "success"]
        failed = [r for r in results if r.get("status") == "error"]

        logger.info(f"Final results: {len(successful)} successful, {len(failed)} failed")

        # Last resort: If EVERYTHING failed, use demo data
        if len(successful) == 0:
            logger.error("All data sources failed - using demo data as last resort")
            if debug_metadata:
                debug_metadata["fetch_order"].append("All sources failed - using demo data fallback")
                # Mark all as demo data source
                for symbol in stock_symbols:
                    debug_metadata["data_sources"][symbol] = "demo_data_fallback"
            demo_results = self._get_demo_data(stock_symbols)
            results = [demo_results[symbol] for symbol in stock_symbols]
            successful = [r for r in results if r.get("status") == "success"]
            failed = []

        # Sort by change percentage
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

        # Check if using demo data
        is_demo = any(s.get("is_demo", False) for s in successful)

        result = {
            "list_name": list_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_demo_data": is_demo,
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

        # Add Claude-friendly format
        if format_for_claude:
            claude_format = self._format_for_claude(result)
            result["claude_summary"] = claude_format["text_summary"]

        # Add debug metadata if requested
        if debug_metadata:
            debug_metadata["summary"] = {
                "yfinance_download_count": sum(1 for src in debug_metadata["data_sources"].values() if src == "yfinance"),
                "yfinance_ticker_api_count": sum(1 for src in debug_metadata["data_sources"].values() if src == "yfinance_ticker_api"),
                "llm_search_count": sum(1 for src in debug_metadata["data_sources"].values() if src == "llm_search"),
                "web_scraping_count": sum(1 for src in debug_metadata["data_sources"].values() if src == "web_scraping"),
                "demo_data_count": sum(1 for src in debug_metadata["data_sources"].values() if src == "demo_data_fallback"),
                "failed_count": sum(1 for src in debug_metadata["data_sources"].values() if src == "failed"),
                "validation_warnings_count": len(debug_metadata["validation_warnings"]),
                "has_warnings": len(debug_metadata["validation_warnings"]) > 0
            }
            result["_debug"] = debug_metadata

        # Cache the result (but don't cache debug metadata)
        result_to_cache = {k: v for k, v in result.items() if k != "_debug"}
        self._cache[cache_key] = result_to_cache
        self._cache_time = datetime.now(timezone.utc)

        return result


# Singleton instance
stock_monitor_agent = StockMonitorAgent()
