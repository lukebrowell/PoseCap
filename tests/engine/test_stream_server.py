import socket
from contextlib import suppress
from pathlib import Path
from queue import Queue
from threading import Thread

import pytest
from posecap_contracts import decode_pose_frame
from posecap_engine.frame_sources import FixtureFrameSource
from posecap_engine.logging_config import configure_logging
from posecap_engine.stream_server import serve_once
from posecap_engine.watchdog import ParentWatchdog

FIXTURES = Path(__file__).parents[1] / "contracts" / "fixtures"


@pytest.mark.integration
def test_fixture_stream_serves_schema_valid_ndjson(tmp_path: Path) -> None:
    fixture = _combined_fixture(tmp_path)
    source = FixtureFrameSource(fixture)
    run = _ServerRun(source.frames())
    run.start()

    with socket.create_connection(run.address(), timeout=2) as client:
        reader = client.makefile("r", encoding="utf-8")
        first = decode_pose_frame(reader.readline())
        second = decode_pose_frame(reader.readline())
        assert reader.readline() == ""

    run.join()
    assert (first.seq, first.status) == (42, "ok")
    assert (second.seq, second.status) == (43, "no_person")


@pytest.mark.integration
def test_stream_server_exits_when_client_disconnects(tmp_path: Path) -> None:
    fixture = _combined_fixture(tmp_path)
    source = FixtureFrameSource(fixture, repeat=True, frame_interval_seconds=0.01)
    run = _ServerRun(source.frames())
    run.start()

    client = socket.create_connection(run.address(), timeout=2)
    reader = client.makefile("r", encoding="utf-8")
    assert decode_pose_frame(reader.readline()).seq == 42
    reader.close()
    with suppress(OSError):
        client.shutdown(socket.SHUT_RDWR)
    client.close()

    run.join()


@pytest.mark.integration
def test_stream_server_exits_when_parent_watchdog_fails(tmp_path: Path) -> None:
    fixture = _combined_fixture(tmp_path)
    watchdog = ParentWatchdog(123, probe=lambda pid: pid != 123)
    run = _ServerRun(FixtureFrameSource(fixture).frames(), watchdog=watchdog)
    run.start()

    run.address()
    run.join()


class _ServerRun:
    def __init__(
        self,
        frames,
        *,
        watchdog: ParentWatchdog | None = None,
    ) -> None:
        self._ready: Queue[tuple[str, int]] = Queue()
        self._errors: Queue[BaseException] = Queue()
        self._thread = Thread(
            target=self._run,
            args=(frames, watchdog),
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def address(self) -> tuple[str, int]:
        return self._ready.get(timeout=2)

    def join(self) -> None:
        self._thread.join(timeout=2)
        if self._thread.is_alive():
            raise AssertionError("server thread did not exit")
        if not self._errors.empty():
            raise self._errors.get()

    def _run(self, frames, watchdog: ParentWatchdog | None) -> None:
        try:
            serve_once(
                frames,
                watchdog=watchdog,
                logger=configure_logging(None),
                ready=self._ready.put,
            )
        except BaseException as exc:
            self._errors.put(exc)


def _combined_fixture(tmp_path: Path) -> Path:
    fixture = tmp_path / "frames.ndjson"
    fixture.write_text(
        "\n".join(
            [
                (FIXTURES / "pose_frame_ok.json").read_text(encoding="utf-8").strip(),
                (FIXTURES / "pose_frame_no_person.json").read_text(encoding="utf-8").strip(),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return fixture
