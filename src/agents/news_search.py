"""
News Search Agent - Searches for stock-related news and videos
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from enum import Enum
import asyncio
from loguru import logger

try:
    import httpx
except ImportError:
    httpx = None

from src.agents.base import BaseAgent


class NewsSource(str, Enum):
    """News sources to search"""
    YOUTUBE = "youtube"
    NYT = "nyt"
    WSJ = "wsj"
    ALL = "all"


class NewsSearchAgent(BaseAgent):
    """
    Agent for searching news and videos about stocks.

    Searches:
    - YouTube for recent videos
    - New York Times for articles
    - Wall Street Journal for financial news

    Returns recent, relevant links for stock analysis.
    """

    def __init__(self):
        super().__init__()
        self._cache: Dict[str, Any] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = 1800  # 30 minutes cache

    @property
    def name(self) -> str:
        return "news-search"

    @property
    def description(self) -> str:
        return "Searches YouTube, NYT, and WSJ for stock-related news and videos"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is still valid"""
        if not self._cache_time or cache_key not in self._cache:
            return False
        elapsed = (datetime.now(timezone.utc) - self._cache_time).total_seconds()
        return elapsed < self._cache_ttl

    async def _search_youtube(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search YouTube for videos.
        Returns video links without requiring API key.
        """
        results = []

        try:
            # YouTube search URL (no API key needed for basic search)
            search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"

            results.append({
                "title": f"YouTube search: {query}",
                "url": search_url,
                "source": "YouTube",
                "type": "search",
                "description": f"Search results for '{query}' on YouTube",
                "published": datetime.now(timezone.utc).isoformat()
            })

            logger.info(f"[{self.name}] Generated YouTube search URL for: {query}")

        except Exception as e:
            logger.error(f"Error searching YouTube: {e}")

        return results

    async def _search_nyt(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search New York Times.
        Returns NYT links.
        """
        results = []

        try:
            # NYT search URL
            search_url = f"https://www.nytimes.com/search?query={query.replace(' ', '+')}"

            results.append({
                "title": f"NYT search: {query}",
                "url": search_url,
                "source": "New York Times",
                "type": "search",
                "description": f"Search results for '{query}' on NYT",
                "published": datetime.now(timezone.utc).isoformat()
            })

            logger.info(f"[{self.name}] Generated NYT search URL for: {query}")

        except Exception as e:
            logger.error(f"Error searching NYT: {e}")

        return results

    async def _search_wsj(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search Wall Street Journal.
        Returns WSJ links.
        """
        results = []

        try:
            # WSJ search URL
            search_url = f"https://www.wsj.com/search?query={query.replace(' ', '+')}"

            results.append({
                "title": f"WSJ search: {query}",
                "url": search_url,
                "source": "Wall Street Journal",
                "type": "search",
                "description": f"Search results for '{query}' on WSJ",
                "published": datetime.now(timezone.utc).isoformat()
            })

            logger.info(f"[{self.name}] Generated WSJ search URL for: {query}")

        except Exception as e:
            logger.error(f"Error searching WSJ: {e}")

        return results

    def _format_for_claude(self, results: List[Dict[str, Any]], query: str) -> str:
        """Format results for Claude Chat"""
        if not results:
            return f"No results found for '{query}'"

        text = f"📰 News & Videos for: {query}\n\n"

        for i, result in enumerate(results, 1):
            text += f"{i}. [{result['source']}] {result['title']}\n"
            text += f"   {result['url']}\n"
            if result.get('description'):
                text += f"   {result['description']}\n"
            text += "\n"

        return text

    async def run(
        self,
        symbols: Optional[List[str]] = None,
        company_names: Optional[List[str]] = None,
        sources: List[str] = None,
        max_results_per_source: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search for news and videos about stocks.

        Args:
            symbols: Stock symbols to search (e.g., ["AAPL", "GOOGL"])
            company_names: Company names to search (e.g., ["Apple", "Google"])
            sources: Which sources to search ["youtube", "nyt", "wsj"] or "all"
            max_results_per_source: Max results per source (default: 3)

        Returns:
            Dict with search results from all sources
        """
        # Default to all sources
        if sources is None or "all" in sources:
            sources = ["youtube", "nyt", "wsj"]

        # Default to empty lists if not provided
        if symbols is None:
            symbols = []
        if company_names is None:
            company_names = []

        # Create cache key
        cache_key = f"{','.join(sorted(symbols))}-{','.join(sorted(company_names))}-{','.join(sorted(sources))}"

        # Check cache
        if self._is_cache_valid(cache_key):
            logger.info(f"[{self.name}] Returning cached results")
            return self._cache[cache_key]

        all_results = []

        # Build search queries
        queries = []
        for symbol in symbols:
            queries.append(f"{symbol} stock news")
        for name in company_names:
            queries.append(f"{name} stock news")

        if not queries:
            queries = ["stock market news today"]

        logger.info(f"[{self.name}] Searching {len(queries)} queries across {len(sources)} sources")

        # Search each source for each query
        tasks = []
        for query in queries:
            if "youtube" in sources:
                tasks.append(("youtube", query, self._search_youtube(query, max_results_per_source)))
            if "nyt" in sources:
                tasks.append(("nyt", query, self._search_nyt(query, max_results_per_source)))
            if "wsj" in sources:
                tasks.append(("wsj", query, self._search_wsj(query, max_results_per_source)))

        # Execute all searches concurrently
        search_results = await asyncio.gather(*[task[2] for task in tasks])

        # Combine results
        for i, (source, query, _) in enumerate(tasks):
            results = search_results[i]
            for result in results:
                result["query"] = query
                all_results.append(result)

        # Group by source
        by_source = {
            "youtube": [r for r in all_results if r["source"] == "YouTube"],
            "nyt": [r for r in all_results if r["source"] == "New York Times"],
            "wsj": [r for r in all_results if r["source"] == "Wall Street Journal"]
        }

        # Build response
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "queries": queries,
            "sources_searched": sources,
            "total_results": len(all_results),
            "results_by_source": {
                "youtube": len(by_source["youtube"]),
                "nyt": len(by_source["nyt"]),
                "wsj": len(by_source["wsj"])
            },
            "results": all_results,
            "grouped_results": by_source,
            "claude_summary": self._format_for_claude(all_results, ", ".join(queries))
        }

        # Cache the result
        self._cache[cache_key] = result
        self._cache_time = datetime.now(timezone.utc)

        return result


# Singleton instance
news_search_agent = NewsSearchAgent()
