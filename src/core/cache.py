"""
Persistent cache storage layer for stock data
Uses SQLite for persistent storage with automatic cleanup
"""

import sqlite3
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path
from loguru import logger
import threading


class StockCache:
    """
    Persistent cache for stock data using SQLite.

    Features:
    - Persistent storage (survives server restarts)
    - Configurable TTL (default: 30 minutes)
    - Automatic cleanup of expired entries
    - Thread-safe operations
    - Batch operations for efficiency
    """

    def __init__(self, db_path: str = "data/stock_cache.db", ttl_seconds: int = 1800):
        """
        Initialize the cache.

        Args:
            db_path: Path to SQLite database file
            ttl_seconds: Time-to-live for cache entries (default: 1800 = 30 minutes)
        """
        self.db_path = db_path
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()

        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

        logger.info(f"✓ Stock cache initialized: {db_path} (TTL: {ttl_seconds}s)")

    def _init_db(self):
        """Create database schema if it doesn't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_cache (
                    symbol TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            """)

            # Create index on expires_at for efficient cleanup
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at
                ON stock_cache(expires_at)
            """)

            conn.commit()

    def get(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get cached data for a single symbol.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')

        Returns:
            Stock data dict if found and not expired, None otherwise
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT data, expires_at
                    FROM stock_cache
                    WHERE symbol = ? AND expires_at > ?
                    """,
                    (symbol.upper(), datetime.now(timezone.utc).isoformat())
                )

                row = cursor.fetchone()
                if row:
                    data_json, expires_at = row
                    data = json.loads(data_json)
                    logger.debug(f"Cache HIT: {symbol} (expires: {expires_at})")
                    return data
                else:
                    logger.debug(f"Cache MISS: {symbol}")
                    return None

    def get_many(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get cached data for multiple symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            Dict mapping symbols to their data (only includes found & valid entries)
        """
        if not symbols:
            return {}

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                # Use parameterized query with IN clause
                placeholders = ','.join('?' * len(symbols))
                now = datetime.now(timezone.utc).isoformat()

                cursor = conn.execute(
                    f"""
                    SELECT symbol, data
                    FROM stock_cache
                    WHERE symbol IN ({placeholders}) AND expires_at > ?
                    """,
                    [s.upper() for s in symbols] + [now]
                )

                results = {}
                for symbol, data_json in cursor.fetchall():
                    results[symbol] = json.loads(data_json)

                hit_count = len(results)
                miss_count = len(symbols) - hit_count
                logger.debug(f"Cache batch: {hit_count} hits, {miss_count} misses")

                return results

    def set(self, symbol: str, data: Dict[str, Any], ttl_seconds: Optional[int] = None):
        """
        Cache data for a single symbol.

        Args:
            symbol: Stock symbol
            data: Stock data dict
            ttl_seconds: Optional custom TTL (uses default if not specified)
        """
        ttl = ttl_seconds or self.ttl_seconds
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl)

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO stock_cache (symbol, data, timestamp, expires_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        symbol.upper(),
                        json.dumps(data),
                        now.isoformat(),
                        expires_at.isoformat()
                    )
                )
                conn.commit()

        logger.debug(f"Cached: {symbol} (expires: {expires_at.isoformat()})")

    def set_many(self, data_dict: Dict[str, Dict[str, Any]], ttl_seconds: Optional[int] = None):
        """
        Cache data for multiple symbols in a batch.

        Args:
            data_dict: Dict mapping symbols to their data
            ttl_seconds: Optional custom TTL (uses default if not specified)
        """
        if not data_dict:
            return

        ttl = ttl_seconds or self.ttl_seconds
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl)

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                # Batch insert for efficiency
                data_rows = [
                    (
                        symbol.upper(),
                        json.dumps(data),
                        now.isoformat(),
                        expires_at.isoformat()
                    )
                    for symbol, data in data_dict.items()
                ]

                conn.executemany(
                    """
                    INSERT OR REPLACE INTO stock_cache (symbol, data, timestamp, expires_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    data_rows
                )
                conn.commit()

        logger.info(f"✓ Cached {len(data_dict)} stocks (expires: {expires_at.isoformat()})")

    def get_all_cached(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all valid cached stocks.

        Returns:
            Dict mapping all cached symbols to their data
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT symbol, data
                    FROM stock_cache
                    WHERE expires_at > ?
                    ORDER BY symbol
                    """,
                    (datetime.now(timezone.utc).isoformat(),)
                )

                results = {}
                for symbol, data_json in cursor.fetchall():
                    results[symbol] = json.loads(data_json)

                logger.debug(f"Retrieved {len(results)} cached stocks")
                return results

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM stock_cache
                    WHERE expires_at <= ?
                    """,
                    (datetime.now(timezone.utc).isoformat(),)
                )
                deleted = cursor.rowcount
                conn.commit()

        if deleted > 0:
            logger.info(f"✓ Cleaned up {deleted} expired cache entries")

        return deleted

    def clear(self):
        """Clear all cached data"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM stock_cache")
                deleted = cursor.rowcount
                conn.commit()

        logger.info(f"✓ Cleared all cache ({deleted} entries)")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache statistics
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                # Count total entries
                cursor = conn.execute("SELECT COUNT(*) FROM stock_cache")
                total = cursor.fetchone()[0]

                # Count valid (non-expired) entries
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM stock_cache WHERE expires_at > ?",
                    (datetime.now(timezone.utc).isoformat(),)
                )
                valid = cursor.fetchone()[0]

                # Get oldest and newest entries
                cursor = conn.execute(
                    """
                    SELECT MIN(timestamp), MAX(timestamp)
                    FROM stock_cache
                    WHERE expires_at > ?
                    """,
                    (datetime.now(timezone.utc).isoformat(),)
                )
                oldest, newest = cursor.fetchone()

        return {
            "total_entries": total,
            "valid_entries": valid,
            "expired_entries": total - valid,
            "oldest_entry": oldest,
            "newest_entry": newest,
            "ttl_seconds": self.ttl_seconds,
            "db_path": self.db_path
        }


# Singleton instance
_cache_instance: Optional[StockCache] = None


def get_cache() -> StockCache:
    """Get or create the global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = StockCache()
    return _cache_instance
