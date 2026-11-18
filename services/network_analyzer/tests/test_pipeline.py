import hashlib
import logging
from pathlib import Path

import pytest
from pcap.models import DiscoveredPcap
from pipeline import Pipeline

from tests.builders import handshake_packets, sample_metrics, truncated_record_pcap_bytes, write_pcap
from tests.queries import COUNT_NETWORK_METRICS, SELECT_NETWORK_METRIC_ROWS, SELECT_PCAP_FILENAMES
from utils.db import Application, insert_network_metrics
from utils.db.connection import get_db_cursor


def _write_synthetic_pcap(root: Path, app_folder: str, scenario: str, filename: str) -> Path:
    """Write one real synthetic capture below the pcap root and return its path."""
    pcap_path = root / app_folder / scenario / filename
    pcap_path.parent.mkdir(parents=True)
    write_pcap(pcap_path, handshake_packets())
    return pcap_path


def _query_rows(query: str, parameters: tuple = ()) -> list:
    """Run one read-only query and return its raw rows."""
    with get_db_cursor() as cursor:
        cursor.execute(query, parameters)
        return cursor.fetchall()


def test_matches_app_title_case_insensitively_and_persists_the_real_metrics(clean_database, seed_application, tmp_path):
    app_id = seed_application("Baham", "ir.android.baham")
    pcap_path = _write_synthetic_pcap(tmp_path, "BAHAM", "upload", "capture.pcap")

    Pipeline(pcap_root=tmp_path).run()

    assert _query_rows(SELECT_NETWORK_METRIC_ROWS) == [
        (
            app_id,
            "upload",
            "capture.pcap",
            hashlib.sha256(pcap_path.read_bytes()).hexdigest(),
            pytest.approx(0.05),
            0,
            0,
            0,
            262,
            100,
            pytest.approx(162 / 262),
            443,
        )
    ]


def test_skips_an_application_without_pcap_files(clean_database, seed_application, tmp_path):
    seed_application("Baham", "ir.android.baham")
    (tmp_path / "Baham").mkdir()

    Pipeline(pcap_root=tmp_path).run()

    assert _query_rows(COUNT_NETWORK_METRICS) == [(0,)]


def test_missing_pcap_root_skips_the_cycle(clean_database, tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        Pipeline(pcap_root=tmp_path / "missing").run()

    assert any("root directory not found" in record.message for record in caplog.records)
    assert _query_rows(COUNT_NETWORK_METRICS) == [(0,)]


def test_parse_failure_on_one_pcap_does_not_stop_the_rest(clean_database, seed_application, tmp_path, caplog):
    seed_application("Baham", "ir.android.baham")
    broken_pcap = tmp_path / "Baham" / "upload" / "broken.pcap"
    broken_pcap.parent.mkdir(parents=True)
    broken_pcap.write_bytes(truncated_record_pcap_bytes())
    _write_synthetic_pcap(tmp_path, "Baham", "download", "valid.pcap")

    with caplog.at_level(logging.ERROR):
        Pipeline(pcap_root=tmp_path).run()

    assert _query_rows(SELECT_PCAP_FILENAMES) == [("valid.pcap",)]
    assert any("Failed to analyze" in record.message for record in caplog.records)


def test_duplicate_hash_is_skipped_without_reanalysis(clean_database, seed_application, tmp_path, caplog):
    app_id = seed_application("Baham", "ir.android.baham")
    pcap_path = _write_synthetic_pcap(tmp_path, "Baham", "upload", "capture.pcap")
    insert_network_metrics(app_id, sample_metrics(hashlib.sha256(pcap_path.read_bytes()).hexdigest()).to_record())

    with caplog.at_level(logging.INFO):
        Pipeline(pcap_root=tmp_path).run()

    assert _query_rows(COUNT_NETWORK_METRICS) == [(1,)]
    assert any("duplicate hash" in record.message for record in caplog.records)
    assert not any("Analyzing" in record.message for record in caplog.records)


def test_insert_failure_on_one_pcap_does_not_stop_the_rest(clean_database, seed_application, tmp_path, caplog):
    seed_application("Baham", "ir.android.baham")
    upload_pcap = _write_synthetic_pcap(tmp_path, "Baham", "upload", "a.pcap")
    download_pcap = _write_synthetic_pcap(tmp_path, "Baham", "download", "b.pcap")
    discovered = [
        DiscoveredPcap(app_name="Baham", scenario="upload", pcap_path=upload_pcap, pcap_hash="a" * 64),
        DiscoveredPcap(app_name="Baham", scenario="download", pcap_path=download_pcap, pcap_hash="b" * 64),
    ]
    deleted_application = Application(id=999999, title="Baham", package_name="ir.android.baham")
    pipeline = Pipeline(pcap_root=tmp_path)

    with caplog.at_level(logging.ERROR):
        pipeline._process_application(deleted_application, pipeline._group_by_app_name(discovered))

    assert len([record for record in caplog.records if "Failed to persist metrics" in record.message]) == 2
    assert _query_rows(COUNT_NETWORK_METRICS) == [(0,)]


def test_unmatched_folder_is_logged_as_error(caplog):
    discovered = [
        DiscoveredPcap(app_name="Baham", scenario="upload", pcap_path=Path("/tmp/a.pcap"), pcap_hash="c" * 64),
        DiscoveredPcap(app_name="Unknown", scenario="upload", pcap_path=Path("/tmp/b.pcap"), pcap_hash="d" * 64),
    ]
    applications = [Application(id=7, title="Baham", package_name="ir.android.baham")]

    with caplog.at_level(logging.ERROR):
        Pipeline()._report_unmatched_folders(Pipeline()._group_by_app_name(discovered), applications)

    errors = [record for record in caplog.records if record.levelno == logging.ERROR]
    assert len(errors) == 1
    assert "unknown" in errors[0].getMessage()
