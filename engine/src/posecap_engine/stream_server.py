"""Single-client TCP NDJSON pose stream server."""

import logging
import select
import socket
from collections.abc import Callable, Iterable

from posecap_contracts import PoseFrame, encode_pose_frame

from .config import DEFAULT_HOST, DEFAULT_PORT
from .errors import StreamServerError
from .logging_config import FrameRateLogger
from .watchdog import ParentWatchdog

ReadyCallback = Callable[[tuple[str, int]], None]


class PoseStreamServer:
    """Serve pose frames to one localhost TCP client."""

    def __init__(
        self,
        frames: Iterable[PoseFrame],
        *,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        watchdog: ParentWatchdog | None = None,
        logger: logging.Logger | None = None,
        ready: ReadyCallback | None = None,
    ) -> None:
        self._frames = frames
        self._host = host
        self._port = port
        self._watchdog = watchdog or ParentWatchdog(None)
        self._logger = logger or logging.getLogger("posecap_engine")
        self._ready = ready

    def serve_once(self) -> None:
        with _listening_socket(self._host, self._port) as server:
            address = server.getsockname()
            if not isinstance(address, tuple) or len(address) < 2:
                raise StreamServerError(f"unexpected socket address: {address!r}")
            bound = (str(address[0]), int(address[1]))
            if self._ready is not None:
                self._ready(bound)
            connection = self._accept(server)
            if connection is None:
                return
            with connection:
                self._write_frames(connection)

    def _accept(self, server: socket.socket) -> socket.socket | None:
        server.settimeout(0.2)
        while self._watchdog.alive():
            try:
                connection, _client_address = server.accept()
                return connection
            except TimeoutError:
                continue
        self._logger.info("parent process exited before stream client connected")
        return None

    def _write_frames(self, connection: socket.socket) -> None:
        rate_logger = FrameRateLogger(self._logger)
        stream = connection.makefile("wb")
        with stream:
            for frame in self._frames:
                if not self._watchdog.alive():
                    self._logger.info("parent process exited during stream")
                    return
                if _client_disconnected(connection):
                    self._logger.info("stream client disconnected")
                    return
                try:
                    stream.write(encode_pose_frame(frame).encode("utf-8") + b"\n")
                    stream.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    self._logger.info("stream client disconnected")
                    return
                rate_logger.frame_sent()


def _listening_socket(host: str, port: int) -> socket.socket:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen(1)
        return server
    except OSError as exc:
        server.close()
        raise StreamServerError(f"could not listen on {host}:{port}: {exc}") from exc


def serve_once(
    frames: Iterable[PoseFrame],
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    watchdog: ParentWatchdog | None = None,
    logger: logging.Logger | None = None,
    ready: ReadyCallback | None = None,
) -> None:
    PoseStreamServer(
        frames,
        host=host,
        port=port,
        watchdog=watchdog,
        logger=logger,
        ready=ready,
    ).serve_once()


def _client_disconnected(connection: socket.socket) -> bool:
    readable, _writable, _errored = select.select([connection], [], [], 0)
    if not readable:
        return False
    try:
        return connection.recv(1, socket.MSG_PEEK) == b""
    except (BlockingIOError, ConnectionResetError, OSError):
        return True
