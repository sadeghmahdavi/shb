import logging
from datetime import timedelta

from configs import CRAWL_INTERVAL_HOURS, SCHEDULER_JOB_ID
from job import create_scheduler, execute_crawl_job


class _StubCrawler:
    """Crawler double whose run() records cycles or raises, without touching the database."""

    def __init__(self, fail: bool = False) -> None:
        self.cycles = 0
        self._fail = fail

    def run(self) -> None:
        if self._fail:
            raise ConnectionError("no route")
        self.cycles += 1


def test_registers_the_periodic_crawl_job():
    scheduler = create_scheduler()

    job = scheduler.get_job(SCHEDULER_JOB_ID)

    assert job is not None
    assert job.trigger.interval == timedelta(hours=CRAWL_INTERVAL_HOURS)
    assert job.next_run_time is not None


def test_runs_the_pipeline_and_logs_completion(caplog):
    crawler = _StubCrawler()

    with caplog.at_level(logging.INFO):
        execute_crawl_job(crawler)

    assert crawler.cycles == 1
    assert any("Crawl cycle completed" in record.message for record in caplog.records)


def test_pipeline_failure_is_logged_not_raised(caplog):
    with caplog.at_level(logging.ERROR):
        execute_crawl_job(_StubCrawler(fail=True))

    assert any("Crawl cycle failed" in record.message for record in caplog.records)
