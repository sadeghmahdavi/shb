import random
import time
from datetime import UTC, datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from configs import CRAWL_INTERVAL_HOURS, DELAY_RANGE, SCHEDULER_JOB_ID, TARGET_REVIEWS_COUNT
from scraper import PlayStoreScraper

from utils.db import Application, fetch_active_apps, insert_app_metrics, upsert_reviews
from utils.logging_setup import get_logger

logger = get_logger(__name__)


class Crawler:
    """Runs one crawl cycle: scrapes and persists metrics and reviews for every active application."""

    def __init__(self, scraper: PlayStoreScraper | None = None) -> None:
        """Take the scraper as an injectable dependency; the default scrapes the real store."""
        self.scraper = scraper if scraper is not None else PlayStoreScraper()

    def run(self) -> None:
        """Run one crawl cycle over every active application, pausing between applications."""
        apps = fetch_active_apps()
        if not apps:
            logger.warning("No active applications found; skipping cycle.")
            return

        for app in apps:
            self._process_app(app)
            time.sleep(random.uniform(*DELAY_RANGE))

    def _process_app(self, app: Application) -> None:
        """Persist one application's metrics and reviews; a failure on either part does not block the other."""
        package_name = app.package_name
        logger.info("Processing %s (%s)", app.title, package_name)

        try:
            metrics = self.scraper.get_app_metrics(package_name)
            if metrics:
                insert_app_metrics(app.id, metrics.to_record())
                logger.info("Persisted metrics for %s", package_name)
        except Exception:
            logger.exception("Failed to persist metrics for %s", package_name)

        try:
            app_reviews = self.scraper.get_latest_reviews(package_name, count=TARGET_REVIEWS_COUNT)
            if app_reviews:
                upsert_reviews(app.id, app_reviews)
                logger.info("Persisted %d reviews for %s", len(app_reviews), package_name)
        except Exception:
            logger.exception("Failed to persist reviews for %s", package_name)


def execute_crawl_job(crawler: Crawler) -> None:
    """Run one crawl cycle, logging instead of raising so the scheduler keeps scheduling."""
    try:
        logger.info("Starting crawl cycle")
        crawler.run()
        logger.info("Crawl cycle completed")
    except Exception:
        logger.exception("Crawl cycle failed")


def create_scheduler() -> BlockingScheduler:
    """Register the recurring crawl job on a blocking UTC scheduler."""
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        execute_crawl_job,
        args=[Crawler()],
        trigger="interval",
        hours=CRAWL_INTERVAL_HOURS,
        id=SCHEDULER_JOB_ID,
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        next_run_time=datetime.now(UTC),
    )
    return scheduler
