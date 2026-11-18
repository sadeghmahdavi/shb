import logging
import os

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def get_logger(logger_name: str) -> logging.Logger:
    """Configure root logging once, from the LOG_LEVEL env var (default INFO), and return the named logger."""
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(), format=LOG_FORMAT)
    return logging.getLogger(logger_name)
