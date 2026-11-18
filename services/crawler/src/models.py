from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from configs import FALLBACK_VERSION_LABEL


def _to_iso_timestamp(value: Any) -> str | None:
    """Convert epoch seconds, datetime objects, or ISO strings into a UTC ISO-8601 string."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC).isoformat()
    if isinstance(value, datetime):
        dt = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return dt.isoformat()
    if isinstance(value, str):
        return value
    return None


@dataclass(frozen=True)
class Review:
    """One Play Store review, translated from the raw scraper payload into the reviews-table shape."""

    review_id: str
    user_name: str | None
    score: int | None
    thumbs_up_count: int
    content: str
    review_at: str | None
    scraped_at: str

    @classmethod
    def from_scraped_payload(cls, payload: dict[str, Any], scraped_at: str | None = None) -> "Review | None":
        raw_id = payload.get("reviewId")
        if not raw_id:
            return None

        now_iso = scraped_at or datetime.now(UTC).isoformat()
        return cls(
            review_id=str(raw_id),
            user_name=payload.get("userName"),
            score=payload.get("score"),
            thumbs_up_count=int(payload.get("thumbsUpCount") or 0),
            content=payload.get("content") or "",
            review_at=_to_iso_timestamp(payload.get("at")),
            scraped_at=now_iso,
        )

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AppMetrics:
    """One app's store metrics, translated from the raw scraper payload into the app_metrics-table shape."""

    min_installs: int | None
    real_installs: int | None
    score: float
    ratings: int | None
    reviews_count: int | None
    version: str
    ad_supported: bool
    store_updated_at: str | None
    scraped_at: str

    @classmethod
    def from_scraped_payload(cls, payload: dict[str, Any], scraped_at: str | None = None) -> "AppMetrics":
        raw_score = payload.get("score")
        score = round(float(raw_score), 2) if raw_score is not None else 0.0

        raw_version = payload.get("version")
        version = str(raw_version) if raw_version else FALLBACK_VERSION_LABEL

        now_iso = scraped_at or datetime.now(UTC).isoformat()
        return cls(
            min_installs=payload.get("minInstalls"),
            real_installs=payload.get("realInstalls"),
            score=score,
            ratings=payload.get("ratings"),
            reviews_count=payload.get("reviews"),
            version=version,
            ad_supported=bool(payload.get("adSupported")),
            store_updated_at=_to_iso_timestamp(payload.get("updated")),
            scraped_at=now_iso,
        )

    def to_record(self) -> dict[str, Any]:
        return asdict(self)