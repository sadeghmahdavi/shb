from dataclasses import replace
from decimal import Decimal

from models import AppMetrics, Review

from tests.queries import (
    INSERT_ACTIVE_AND_INACTIVE_APPLICATIONS,
    SELECT_APP_METRICS_ROW,
    SELECT_REVIEW_CONTENTS,
)
from utils.db import Application, fetch_active_apps, insert_app_metrics, upsert_reviews
from utils.db.connection import get_db_cursor


def metrics_model() -> AppMetrics:
    """Build one AppMetrics model carrying the values the store round-trip asserts on."""
    return AppMetrics(
        min_installs=1000000,
        real_installs=950000,
        score=4.57,
        ratings=50000,
        reviews_count=3000,
        version="3.2.1",
        ad_supported=True,
        store_updated_at="2026-11-14T10:00:00+00:00",
        scraped_at="2026-11-14T10:00:00+00:00",
    )


def review_model(review_id: str, content: str) -> Review:
    """Build one Review model carrying the values the store round-trip asserts on."""
    return Review(
        review_id=review_id,
        user_name="Reviewer",
        score=5,
        thumbs_up_count=0,
        content=content,
        review_at="2026-11-14T09:00:00+00:00",
        scraped_at="2026-11-14T10:00:00+00:00",
    )


def test_returns_only_active_applications(clean_database):
    with get_db_cursor() as cursor:
        cursor.execute(INSERT_ACTIVE_AND_INACTIVE_APPLICATIONS)

    applications = fetch_active_apps()

    assert len(applications) == 1
    assert applications[0] == Application(
        id=applications[0].id, title="Telegram", package_name="org.telegram.messenger"
    )


def test_persists_one_metrics_row_for_the_application(clean_database, seed_application):
    app_id = seed_application("Telegram", "org.telegram.messenger")

    insert_app_metrics(app_id, metrics_model().to_record())

    with get_db_cursor() as cursor:
        cursor.execute(SELECT_APP_METRICS_ROW, (app_id,))
        row = cursor.fetchone()
    assert row == (1000000, Decimal("4.57"), "3.2.1", True)


def test_rerunning_the_same_review_updates_instead_of_duplicating(clean_database, seed_application):
    app_id = seed_application("Telegram", "org.telegram.messenger")

    upsert_reviews(app_id, [review_model("r1", "first").to_record()])
    second_run = [review_model("r1", "updated"), replace(review_model("r1", "second"), review_id="r2")]
    upsert_reviews(app_id, [record.to_record() for record in second_run])

    with get_db_cursor() as cursor:
        cursor.execute(SELECT_REVIEW_CONTENTS, (app_id,))
        rows = cursor.fetchall()
    assert rows == [("r1", "updated"), ("r2", "second")]
