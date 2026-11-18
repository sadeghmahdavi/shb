from tests.builders import sample_metrics
from tests.queries import SELECT_NETWORK_METRIC_ROWS
from utils.db import find_network_metrics_by_hash, insert_network_metrics
from utils.db.connection import get_db_cursor


def test_persists_one_metrics_row_for_the_application(clean_database, seed_application):
    app_id = seed_application("Baham", "ir.android.baham")

    insert_network_metrics(app_id, sample_metrics("a" * 64).to_record())

    with get_db_cursor() as cursor:
        cursor.execute(SELECT_NETWORK_METRIC_ROWS)
        rows = cursor.fetchall()
    assert rows == [
        (
            app_id,
            "upload",
            "capture.pcap",
            "a" * 64,
            0.05,
            1,
            2,
            0,
            262,
            100,
            0.618,
            443,
        )
    ]


def test_returns_the_row_id_when_the_hash_exists(clean_database, seed_application):
    app_id = seed_application("Baham", "ir.android.baham")
    insert_network_metrics(app_id, sample_metrics("b" * 64).to_record())

    assert find_network_metrics_by_hash("b" * 64) == 1


def test_returns_none_for_an_unknown_hash(clean_database):
    assert find_network_metrics_by_hash("c" * 64) is None
