"""
Background task scheduler for proactive stock data caching
Uses APScheduler to refresh stock cache every 30 minutes
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone
from loguru import logger
import asyncio

from src.agents.stock_monitor import stock_monitor_agent, STOCK_LISTS
from src.core.cache import get_cache


class StockCacheScheduler:
    """
    Background scheduler for proactive stock data caching.

    Features:
    - Refreshes top stocks every 30 minutes
    - Runs independently of user requests
    - Reduces API calls by batching updates
    - Ensures fresh data is always available
    """

    def __init__(self, refresh_interval_minutes: int = 30):
        """
        Initialize the scheduler.

        Args:
            refresh_interval_minutes: How often to refresh stock data (default: 30)
        """
        self.scheduler = AsyncIOScheduler()
        self.refresh_interval_minutes = refresh_interval_minutes
        self._is_running = False

        # Lists of stocks to proactively cache
        self.stock_lists_to_cache = [
            "top_tech",
            "top_sp500",
            "top_diversified"
        ]

        logger.info(f"✓ Stock cache scheduler initialized (interval: {refresh_interval_minutes} min)")

    async def _refresh_stock_cache(self):
        """
        Background task to refresh stock cache.
        Fetches data for all configured stock lists.
        """
        try:
            logger.info("="*80)
            logger.info(f"🔄 Background cache refresh started at {datetime.now(timezone.utc).isoformat()}")
            logger.info("="*80)

            cache = get_cache()

            # Clean up expired entries first
            expired_count = cache.cleanup_expired()
            if expired_count > 0:
                logger.info(f"✓ Cleaned up {expired_count} expired cache entries")

            # Fetch each stock list
            total_stocks = 0
            for list_name in self.stock_lists_to_cache:
                try:
                    logger.info(f"📊 Refreshing {list_name}...")

                    # Fetch stocks for this list
                    result = await stock_monitor_agent.run(
                        category=list_name,
                        skip_cache=True,  # Always fetch fresh data
                        format_for_claude=False,  # Don't need Claude formatting for background task
                        debug=False  # No debug output for background task
                    )

                    # Count successful stocks
                    successful = result.get("summary", {}).get("successful", 0)
                    total_stocks += successful

                    logger.info(f"✓ {list_name}: {successful} stocks refreshed")

                    # Small delay between lists to avoid rate limiting
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"✗ Failed to refresh {list_name}: {e}")
                    continue

            # Get cache stats
            stats = cache.get_cache_stats()

            logger.info("="*80)
            logger.info(f"✅ Background cache refresh completed")
            logger.info(f"   • Total stocks refreshed: {total_stocks}")
            logger.info(f"   • Cache stats: {stats['valid_entries']} valid, {stats['expired_entries']} expired")
            logger.info(f"   • Next refresh in {self.refresh_interval_minutes} minutes")
            logger.info("="*80)

        except Exception as e:
            logger.error(f"❌ Background cache refresh failed: {e}")
            logger.exception(e)

    def start(self):
        """Start the background scheduler"""
        if self._is_running:
            logger.warning("Scheduler is already running")
            return

        # Add job to refresh cache every N minutes
        self.scheduler.add_job(
            self._refresh_stock_cache,
            trigger=IntervalTrigger(minutes=self.refresh_interval_minutes),
            id="refresh_stock_cache",
            name="Refresh Stock Cache",
            replace_existing=True,
            max_instances=1  # Prevent overlapping executions
        )

        # Start the scheduler
        self.scheduler.start()
        self._is_running = True

        logger.info(f"✓ Stock cache scheduler started (refresh every {self.refresh_interval_minutes} min)")

        # Run initial refresh immediately in background
        asyncio.create_task(self._refresh_initial_cache())

    async def _refresh_initial_cache(self):
        """Run initial cache refresh on startup"""
        # Wait a few seconds to let server initialize
        await asyncio.sleep(5)

        logger.info("🚀 Running initial stock cache refresh...")
        await self._refresh_stock_cache()

    def stop(self):
        """Stop the background scheduler"""
        if not self._is_running:
            logger.warning("Scheduler is not running")
            return

        self.scheduler.shutdown(wait=True)
        self._is_running = False

        logger.info("✓ Stock cache scheduler stopped")

    def get_jobs(self):
        """Get list of scheduled jobs"""
        return self.scheduler.get_jobs()

    def get_next_run_time(self):
        """Get next scheduled run time"""
        job = self.scheduler.get_job("refresh_stock_cache")
        if job:
            return job.next_run_time
        return None


# Singleton instance
_scheduler_instance = None


def get_scheduler() -> StockCacheScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = StockCacheScheduler()
    return _scheduler_instance
