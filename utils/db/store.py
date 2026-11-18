from typing import Any

from psycopg2.extras import execute_values

from utils.db.connection import get_db_cursor
from utils.db.models import Application
from utils.db.queries import (
    INSERT_APP_METRICS,
    INSERT_NETWORK_METRICS,
    SELECT_ACTIVE_APPLICATIONS,
    SELECT_NETWORK_METRICS_BY_PCAP_HASH,
    UPSERT_REVIEWS,
)
from utils.logging_setup import get_logger

logger = get_logger(__name__)


def fetch_active_apps() -> list[Application]:
    """Every active application in id order — the app list both services crawl and analyze from."""
    with get_db_cursor() as cursor:
        cursor.execute(SELECT_ACTIVE_APPLICATIONS)
        return [Application(id=row[0], title=row[1], package_name=row[2]) for row in cursor.fetchall()]


def insert_app_metrics(app_id: int, metrics: dict[str, Any]) -> None:
    """Store one application's Play Store metrics row."""
    record = (
        app_id,
        metrics.get("min_installs"),
        metrics.get("real_installs"),
        metrics.get("score"),
        metrics.get("ratings"),
        metrics.get("reviews_count"),
        metrics.get("version"),
        metrics.get("ad_supported"),
        metrics.get("store_updated_at"),
        metrics.get("scraped_at"),
    )
    with get_db_cursor() as cursor:
        cursor.execute(INSERT_APP_METRICS, record)


def upsert_reviews(app_id: int, reviews: list[dict[str, Any]]) -> None:
    """Insert one application's review rows, updating the rows whose review_id already exists."""
    if not reviews:
        return

    records = [
        (
            review["review_id"],
            app_id,
            review.get("user_name"),
            review.get("score"),
            review.get("thumbs_up_count", 0),
            review.get("content", ""),
            review.get("review_at"),
            review.get("scraped_at"),
        )
        for review in reviews
    ]
    with get_db_cursor() as cursor:
        execute_values(cursor, UPSERT_REVIEWS, records, page_size=len(records))


def find_network_metrics_by_hash(pcap_hash: str) -> int | None:
    """The id of the stored network_metrics row for one capture content hash, or None when not analyzed yet."""
    with get_db_cursor() as cursor:
        cursor.execute(SELECT_NETWORK_METRICS_BY_PCAP_HASH, (pcap_hash,))
        row = cursor.fetchone()
        return row[0] if row else None


def insert_network_metrics(app_id: int, metrics: dict[str, Any]) -> None:
    """Store one capture's aggregate network metrics row."""
    record = (
        app_id,
        metrics["scenario"],
        metrics["pcap_filename"],
        metrics["pcap_hash"],
        metrics.get("handshake_rtt_avg"),
        metrics.get("retransmission_count", 0),
        metrics.get("zero_window_event_count", 0),
        metrics.get("tcp_reset_drops", 0),
        metrics.get("total_transferred_bytes", 0),
        metrics.get("total_payload_bytes", 0),
        metrics.get("overhead_ratio"),
        metrics.get("dominant_server_port"),
    )
    with get_db_cursor() as cursor:
        cursor.execute(INSERT_NETWORK_METRICS, record)
