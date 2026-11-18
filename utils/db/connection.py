import os
from collections.abc import Generator
from contextlib import contextmanager, suppress

import psycopg2
from psycopg2.extensions import connection as PsycopgConnection
from psycopg2.extensions import cursor as PsycopgCursor

from utils.db.queries import SELECT_HEALTH_CHECK
from utils.logging_setup import get_logger

logger = get_logger(__name__)

DB_NAME = os.getenv("POSTGRES_DB", "sahabino_db")
DB_USER = os.getenv("POSTGRES_USER", "sahabino_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "sahabino_secret_2026")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

_connection: PsycopgConnection | None = None


def _connect() -> PsycopgConnection:
    """Open a fresh psycopg2 connection with TCP keepalives, from the POSTGRES_* env vars."""
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        keepalives=1,
        keepalives_idle=60,
        keepalives_interval=10,
        keepalives_count=5,
    )


def get_db_connection() -> PsycopgConnection:
    """Return the shared live connection, replacing it whenever the SELECT 1 health check fails."""
    global _connection
    if _connection is not None and not _connection.closed:
        try:
            with _connection.cursor() as health_check_cursor:
                health_check_cursor.execute(SELECT_HEALTH_CHECK)
            _connection.rollback()
            return _connection
        except Exception:
            logger.warning("Existing PostgreSQL connection lost; reconnecting.")
    _connection = _connect()
    logger.info("Connected to PostgreSQL %s@%s:%s/%s", DB_USER, DB_HOST, DB_PORT, DB_NAME)
    return _connection


@contextmanager
def get_db_cursor() -> Generator[PsycopgCursor, None, None]:
    """Yield a cursor whose work commits on success and rolls back on any exception."""
    database_connection = get_db_connection()
    database_cursor = database_connection.cursor()
    try:
        yield database_cursor
        database_connection.commit()
    except Exception:
        if not database_connection.closed:
            with suppress(Exception):
                database_connection.rollback()
        raise
    finally:
        database_cursor.close()
