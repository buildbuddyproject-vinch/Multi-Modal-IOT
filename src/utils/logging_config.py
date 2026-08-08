"""Structured logging setup, shared by the API, scripts, and background workers."""
import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        return  # already configured (e.g. re-imported under a test runner)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt="%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Quiet noisy third-party loggers down to warnings only.
    for noisy in ("pymongo", "urllib3", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
