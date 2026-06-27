import logging

from posecap_engine.logging_config import FrameRateLogger


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def test_frame_rate_logger_logs_only_after_interval(monkeypatch) -> None:
    times = iter([0.0, 0.25, 1.0])
    monkeypatch.setattr("posecap_engine.logging_config.time.monotonic", lambda: next(times))
    logger = logging.getLogger("posecap_engine.test_frame_rate_logger")
    logger.handlers.clear()
    logger.propagate = False
    handler = _ListHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    rate_logger = FrameRateLogger(logger, interval_seconds=1.0)
    rate_logger.frame_sent()
    rate_logger.frame_sent()

    assert handler.messages == ["stream_fps 2.00"]
