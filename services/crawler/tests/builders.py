from datetime import UTC, datetime
from typing import Any

from google_play_scraper.exceptions import NotFoundError
from scraper import PlayStoreScraper

REVIEWED_AT = datetime(2026, 11, 14, 9, 0, 0, tzinfo=UTC)
STORE_UPDATED_EPOCH_SECONDS = 1731605400


def raw_review(review_id: str, reviewed_at: datetime = REVIEWED_AT) -> dict[str, Any]:
    """Build one raw google-play-scraper review payload (external API shape, not a domain model)."""
    return {
        "reviewId": review_id,
        "userName": "Reviewer",
        "score": 5,
        "thumbsUpCount": 1,
        "content": f"content {review_id}",
        "at": reviewed_at,
    }


class StubPlayStore:
    """Play Store double: serves a fixed app payload and per-package review batches without network traffic.

    Review ids are scoped to the package because review_id is a global primary key shared by every application.
    """

    def __init__(
        self,
        app_payload: dict[str, Any] | None = None,
        not_found: bool = False,
        review_count: int = 0,
        raw_reviews: list[dict[str, Any]] | None = None,
    ) -> None:
        """Fix the served payload; not_found makes app-detail lookups raise NotFoundError."""
        self.app_payload = app_payload
        self.not_found = not_found
        self.review_count = review_count
        self.raw_reviews = raw_reviews
        self.detail_calls: list[dict[str, Any]] = []

    def fetch_app_details(self, package_name: str, **kwargs: Any) -> dict[str, Any] | None:
        """Serve the fixed payload (or raise NotFoundError), recording every request's kwargs."""
        self.detail_calls.append(kwargs)
        if self.not_found:
            raise NotFoundError("not found")
        return self.app_payload

    def fetch_reviews_page(self, package_name: str, **kwargs: Any) -> tuple[list[dict[str, Any]], None]:
        """Serve one page: the fixed batch when configured, else this package's generated batch."""
        if self.raw_reviews is not None:
            return self.raw_reviews, None
        return self.reviews_for_package(package_name), None

    def reviews_for_package(self, package_name: str) -> list[dict[str, Any]]:
        """Build this package's raw review payloads with ids unique per package."""
        return [raw_review(f"{package_name}-{index + 1}") for index in range(self.review_count)]


def stub_scraper(play_store: StubPlayStore) -> PlayStoreScraper:
    """Wire one StubPlayStore double through the scraper's injectable network calls."""
    return PlayStoreScraper(
        fetch_app_details=play_store.fetch_app_details, fetch_reviews_page=play_store.fetch_reviews_page
    )
