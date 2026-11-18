import pytest

from tests.queries import INSERT_APPLICATION_RETURNING_ID, TRUNCATE_ALL_TABLES
from utils.db.connection import get_db_cursor


def truncate_all_tables() -> None:
    """Wipe every table so each test starts from an empty, seed-free database."""
    with get_db_cursor() as cursor:
        cursor.execute(TRUNCATE_ALL_TABLES)


def seed_one_application(title: str, package_name: str, is_active: bool = True) -> int:
    """Insert one application row and return its id."""
    with get_db_cursor() as cursor:
        cursor.execute(INSERT_APPLICATION_RETURNING_ID, (title, package_name, is_active))
        return cursor.fetchone()[0]


@pytest.fixture
def clean_database():
    """Wipe every table before and after each test."""
    truncate_all_tables()
    yield
    truncate_all_tables()


@pytest.fixture
def seed_application():
    """Helper that inserts one application row and returns its id."""
    return seed_one_application
