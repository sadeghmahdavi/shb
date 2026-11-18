from job import Crawler

from tests.builders import StubPlayStore, stub_scraper
from tests.queries import (
    COUNT_APP_METRICS,
    COUNT_APP_METRICS_FOR_APP,
    COUNT_REVIEWS,
    COUNT_REVIEWS_FOR_APP,
    SELECT_APP_IDS_WITH_METRICS,
    SELECT_APP_REVIEW_IDS,
)
from utils.db import Application
from utils.db.connection import get_db_cursor


def _count(query: str, parameters: tuple = ()) -> int:
    """Run one count query and return its single integer result."""
    with get_db_cursor() as cursor:
        cursor.execute(query, parameters)
        return cursor.fetchone()[0]


def test_crawls_every_active_application_into_the_database(monkeypatch, clean_database, seed_application):
    monkeypatch.setattr("job.DELAY_RANGE", (0, 0))
    first_app_id = seed_application("Telegram", "org.telegram.messenger")
    second_app_id = seed_application("WhatsApp", "com.whatsapp")
    scraper = stub_scraper(StubPlayStore(app_payload={"minInstalls": 1000, "score": 4.5}, review_count=2))

    Crawler(scraper=scraper).run()

    with get_db_cursor() as cursor:
        cursor.execute(SELECT_APP_IDS_WITH_METRICS)
        metric_application_ids = [row[0] for row in cursor.fetchall()]
        cursor.execute(SELECT_APP_REVIEW_IDS)
        review_rows = cursor.fetchall()
    assert metric_application_ids == [first_app_id, second_app_id]
    assert review_rows == [
        (first_app_id, "org.telegram.messenger-1"),
        (first_app_id, "org.telegram.messenger-2"),
        (second_app_id, "com.whatsapp-1"),
        (second_app_id, "com.whatsapp-2"),
    ]


def test_skips_the_cycle_when_no_application_is_active(clean_database):
    Crawler(scraper=stub_scraper(StubPlayStore())).run()

    assert _count(COUNT_APP_METRICS) == 0
    assert _count(COUNT_REVIEWS) == 0


def test_persists_metrics_and_reviews_for_one_application(clean_database, seed_application):
    app_id = seed_application("Telegram", "org.telegram.messenger")
    application = Application(id=app_id, title="Telegram", package_name="org.telegram.messenger")
    play_store = StubPlayStore(app_payload={"minInstalls": 1000, "score": 4.5}, review_count=2)

    Crawler(scraper=stub_scraper(play_store))._process_app(application)

    assert _count(COUNT_APP_METRICS_FOR_APP, (app_id,)) == 1
    assert _count(COUNT_REVIEWS_FOR_APP, (app_id,)) == 2


def test_unavailable_app_still_gets_its_reviews(clean_database, seed_application):
    app_id = seed_application("Telegram", "org.telegram.messenger")
    application = Application(id=app_id, title="Telegram", package_name="org.telegram.messenger")

    Crawler(scraper=stub_scraper(StubPlayStore(not_found=True, review_count=1)))._process_app(application)

    assert _count(COUNT_APP_METRICS_FOR_APP, (app_id,)) == 0
    assert _count(COUNT_REVIEWS_FOR_APP, (app_id,)) == 1
