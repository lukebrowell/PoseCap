"""Logging setup for the engine bridge."""

import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import (
    DEFAULT_FPS_LOG_INTERVAL_SECONDS,
    DEFAULT_LOG_BACKUPS,
    DEFAULT_LOG_BYTES,
)


def configure_logging(log_file: Path | None) -> logging.Logger:
    """Create the engine logger with optional rotating file output."""
    logger = logging.getLogger("posecap_engine")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    if log_file is None:
        logger.addHandler(logging.NullHandler())
        return logger

    log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_file,
        maxBytes=DEFAULT_LOG_BYTES,
        backupCount=DEFAULT_LOG_BACKUPS,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    return logger


class FrameRateLogger:
    """Log inference rate on an interval, never per frame."""

    def __init__(
        self,
        logger: logging.Logger,
        *,
        interval_seconds: float = DEFAULT_FPS_LOG_INTERVAL_SECONDS,
    ) -> None:
        self._logger = logger
        self._interval_seconds = interval_seconds
        self._window_started_at = time.monotonic()
        self._frames = 0

    def frame_sent(self) -> None:
        self._frames += 1
        now = time.monotonic()
        elapsed = now - self._window_started_at
        if elapsed < self._interval_seconds:
            return
        fps = self._frames / elapsed if elapsed > 0 else 0.0
        self._logger.info("stream_fps %.2f", fps)
        self._window_started_at = now
        self._frames = 0
