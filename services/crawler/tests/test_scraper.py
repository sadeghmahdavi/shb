from google_play_scraper.exceptions import NotFoundError
from scraper import PlayStoreScraper

from tests.builders import StubPlayStore, stub_scraper


def test_fetches_app_metrics_from_primary_locale():
    play_store = StubPlayStore(
        app_payload={
            "minInstalls": 500000,
            "realInstalls": 480000,
            "score": 4.35,
            "ratings": 12000,
            "reviews": 900,
            "version": "1.2.3",
            "adSupported": False,
            "updated": 1731605400,
        }
    )
    scraper = stub_scraper(play_store)

    metrics = scraper.get_app_metrics("org.telegram.messenger")

    assert metrics is not None
    assert metrics.min_installs == 500000
    assert metrics.version == "1.2.3"
    assert play_store.detail_calls == [{"lang": "en", "country": "us"}]


def test_falls_back_to_iran_locale_when_us_returns_not_found():
    calls: list[dict[str, str]] = []

    def fake_fetch(package_name: str, **kwargs):
        calls.append(kwargs)
        if kwargs.get("country") == "us":
            raise NotFoundError("not in us")
        return {"minInstalls": 100000, "score": 4.1, "version": "2.0.0"}

    scraper = PlayStoreScraper(fetch_app_details=fake_fetch)
    metrics = scraper.get_app_metrics("com.aparat")

    assert metrics is not None
    assert metrics.min_installs == 100000
    assert calls == [{"lang": "en", "country": "us"}, {"lang": "fa", "country": "ir"}]


def test_returns_none_when_app_not_found_in_any_locale():
    scraper = stub_scraper(StubPlayStore(not_found=True))

    assert scraper.get_app_metrics("com.unknown.app") is None


def test_retries_transient_error_and_succeeds(monkeypatch):
    monkeypatch.setattr("scraper.time.sleep", lambda _: None)
    attempts = 0

    def flaky_fetch(package_name: str, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("429 Too Many Requests")
        return {"minInstalls": 2000, "score": 4.8, "version": "1.0.0"}

    scraper = PlayStoreScraper(fetch_app_details=flaky_fetch)
    metrics = scraper.get_app_metrics("com.whatsapp")

    assert metrics is not None
    assert attempts == 3
    assert metrics.min_installs == 2000