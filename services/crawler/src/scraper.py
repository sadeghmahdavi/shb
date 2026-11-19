import random
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from configs import (
    AIMD_DECREASE_STEP,
    AIMD_INCREASE_FACTOR,
    BASE_BACKOFF,
    COUNTRY_CODE,
    INITIAL_ADAPTIVE_DELAY,
    LANG_CODE,
    MAX_ADAPTIVE_DELAY,
    MAX_BACKOFF,
    MAX_RETRIES,
    MIN_ADAPTIVE_DELAY,
    MIN_JITTER_SECONDS,
    POLITE_JITTER_RANGE,
    PROXY_COUNTRY_CODE,
    PROXY_LANG_CODE,
    RATE_LIMIT_MARKERS,
    REVIEW_LOCALES,
    REVIEWS_BATCH_SIZE,
    TARGET_REVIEWS_COUNT,
)
from google_play_scraper import Sort, app, reviews
from google_play_scraper.exceptions import NotFoundError
from models import AppMetrics, Review

from utils.logging_setup import get_logger

logger = get_logger(__name__)


class PlayStoreScraper:
    """Fetches app metrics and reviews from the Play Store with retry/backoff."""

    def __init__(
        self,
        fetch_app_details: Callable[..., Any] = app,
        fetch_reviews_page: Callable[..., Any] = reviews,
    ) -> None:
        """Accept the Play Store calls as injectable dependencies; the defaults hit the real store."""
        self.fetch_app_details = fetch_app_details
        self.fetch_reviews_page = fetch_reviews_page

        self.max_retries = MAX_RETRIES
        self.base_backoff = BASE_BACKOFF
        self.max_backoff = MAX_BACKOFF

        self.adaptive_delay = INITIAL_ADAPTIVE_DELAY
        self.min_delay = MIN_ADAPTIVE_DELAY
        self.max_delay = MAX_ADAPTIVE_DELAY

    def _is_rate_limited(self, exc: Exception) -> bool:
        message = str(exc)
        return any(marker in message for marker in RATE_LIMIT_MARKERS)

    def _call_with_retry(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                self.adaptive_delay = max(self.min_delay, self.adaptive_delay - AIMD_DECREASE_STEP)
                return result
            except NotFoundError:
                raise
            except Exception as exc:
                if self._is_rate_limited(exc):
                    self.adaptive_delay = min(self.max_delay, self.adaptive_delay * AIMD_INCREASE_FACTOR)

                if attempt == self.max_retries - 1:
                    raise

                backoff = min(self.max_backoff, self.base_backoff * (2**attempt))
                jitter = random.uniform(MIN_JITTER_SECONDS, MIN_JITTER_SECONDS + 0.5)
                sleep_seconds = backoff + jitter
                logger.warning(
                    "Transient scraper error (%s); retrying in %.2fs (attempt %d/%d)",
                    exc,
                    sleep_seconds,
                    attempt + 1,
                    self.max_retries,
                )
                time.sleep(sleep_seconds)

    def get_app_metrics(self, package_name: str) -> AppMetrics | None:
        locales = [
            (LANG_CODE, COUNTRY_CODE),
            (PROXY_LANG_CODE, PROXY_COUNTRY_CODE),
        ]

        for lang, country in locales:
            try:
                payload = self._call_with_retry(
                    self.fetch_app_details,
                    package_name,
                    lang=lang,
                    country=country,
                )
                if payload:
                    scraped_at = datetime.now(UTC).isoformat()
                    return AppMetrics.from_scraped_payload(payload, scraped_at=scraped_at)
            except NotFoundError:
                logger.debug("Package %s not found in locale (%s, %s)", package_name, lang, country)
                continue

        logger.warning("Package %s not found in any configured locale", package_name)
        return None

    def get_latest_reviews(self, package_name: str, count: int = TARGET_REVIEWS_COUNT) -> list[dict[str, Any]]:
        if count <= 0:
            return []

        collected: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        scraped_at = datetime.now(UTC).isoformat()

        for lang, country in REVIEW_LOCALES:
            if len(collected) >= count:
                break

            continuation_token = None
            while len(collected) < count:
                batch_size = min(REVIEWS_BATCH_SIZE, count - len(collected))
                try:
                    raw_batch, next_token = self._call_with_retry(
                        self.fetch_reviews_page,
                        package_name,
                        lang=lang,
                        country=country,
                        sort=Sort.NEWEST,
                        count=batch_size,
                        continuation_token=continuation_token,
                    )
                except NotFoundError:
                    logger.debug("Reviews for %s not found in locale (%s, %s)", package_name, lang, country)
                    break
                except Exception:
                    logger.exception("Failed fetching reviews for %s in locale (%s, %s)", package_name, lang, country)
                    break

                if not raw_batch:
                    break

                for raw_item in raw_batch:
                    review = Review.from_scraped_payload(raw_item, scraped_at=scraped_at)
                    if review is None or review.review_id in seen_ids:
                        continue
                    seen_ids.add(review.review_id)
                    collected.append(review.to_record())
                    if len(collected) >= count:
                        break

                if not next_token or next_token == continuation_token or len(collected) >= count:
                    break

                continuation_token = next_token
                time.sleep(self.adaptive_delay + random.uniform(*POLITE_JITTER_RANGE))

        return collected