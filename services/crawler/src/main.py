from configs import CRAWL_INTERVAL_HOURS
from job import create_scheduler

from utils.logging_setup import get_logger

logger = get_logger(__name__)


def main() -> None:
    """Start the blocking scheduler loop; a keyboard interrupt stops it cleanly."""
    scheduler = create_scheduler()
    logger.info("Starting scheduler loop (interval: %s h)", CRAWL_INTERVAL_HOURS)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler process terminated")


if __name__ == "__main__":
    main()
