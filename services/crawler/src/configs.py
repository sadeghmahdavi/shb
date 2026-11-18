import os

CRAWL_INTERVAL_HOURS: int = int(os.getenv("CRAWL_INTERVAL_HOURS", "1"))

DELAY_RANGE: tuple[float, float] = (1, 3)
TARGET_REVIEWS_COUNT: int = 1000
MAX_RETRIES: int = 5
BASE_BACKOFF: float = 1.5
MAX_BACKOFF: float = 20.0
MIN_JITTER_SECONDS: float = 0.5

INITIAL_ADAPTIVE_DELAY: float = 0.4
MIN_ADAPTIVE_DELAY: float = 0.2
MAX_ADAPTIVE_DELAY: float = 3.0
AIMD_DECREASE_STEP: float = 0.05
AIMD_INCREASE_FACTOR: float = 1.8

REVIEWS_BATCH_SIZE: int = 200
POLITE_JITTER_RANGE: tuple[float, float] = (0.1, 0.3)

COUNTRY_CODE = "us"
LANG_CODE = "en"
PROXY_COUNTRY_CODE = "ir"
PROXY_LANG_CODE = "fa"

REVIEW_LOCALES: list[tuple[str, str]] = [
    ("fa", "ir"),
    ("en", "us"),
    ("pt", "br"),
    ("hi", "in"),
    ("en", "gb"),
]

FALLBACK_VERSION_LABEL: str = "Varies with device"
RATE_LIMIT_MARKERS: tuple[str, ...] = ("429", "Too Many Requests")

SCHEDULER_JOB_ID: str = "google_play_crawler_periodic_job"
