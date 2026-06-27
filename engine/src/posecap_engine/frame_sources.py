"""Pose frame producers used by the engine stream server."""

import time
from collections.abc import Iterator
from pathlib import Path

from posecap_contracts import PoseFrame, decode_pose_frame

from .errors import EngineError


class FixtureFrameSource:
    """Read schema-valid pose frames from an NDJSON fixture file."""

    def __init__(
        self,
        path: Path,
        *,
        repeat: bool = False,
        frame_interval_seconds: float = 0.0,
    ) -> None:
        self._path = path
        self._repeat = repeat
        self._frame_interval_seconds = frame_interval_seconds

    def frames(self) -> Iterator[PoseFrame]:
        frames = self._load_frames()
        while True:
            yield from self._pace(frames)
            if not self._repeat:
                return

    def _load_frames(self) -> tuple[PoseFrame, ...]:
        lines = self._path.read_text(encoding="utf-8").splitlines()
        frames = tuple(decode_pose_frame(line) for line in lines if line.strip())
        if not frames:
            raise EngineError(f"fixture contains no pose frames: {self._path}")
        return frames

    def _pace(self, frames: tuple[PoseFrame, ...]) -> Iterator[PoseFrame]:
        for frame in frames:
            yield frame
            if self._frame_interval_seconds > 0:
                time.sleep(self._frame_interval_seconds)
