"""Camera discovery and capture helpers for the engine edge."""

import importlib
from dataclasses import asdict, dataclass
from typing import Any

from .errors import CaptureUnavailableError


@dataclass(frozen=True)
class CameraDevice:
    """A webcam candidate discovered by bounded OpenCV probing."""

    index: int
    name: str
    width: int | None
    height: int | None
    fps: float | None

    def to_json(self) -> dict[str, object]:
        return asdict(self)


def enumerate_devices(max_index: int = 8) -> list[CameraDevice]:
    """Return cameras that OpenCV can open by index."""
    cv2 = _load_cv2()
    devices: list[CameraDevice] = []
    for index in range(max_index + 1):
        capture = cv2.VideoCapture(index)
        try:
            if not bool(capture.isOpened()):
                continue
            devices.append(
                CameraDevice(
                    index=index,
                    name=f"Camera {index}",
                    width=_positive_int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    height=_positive_int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    fps=_positive_float(capture.get(cv2.CAP_PROP_FPS)),
                )
            )
        finally:
            capture.release()
    return devices


def _load_cv2() -> Any:
    try:
        return importlib.import_module("cv2")
    except ImportError as exc:
        raise CaptureUnavailableError("OpenCV is not installed in the engine environment") from exc


def _positive_int(value: object) -> int | None:
    if not isinstance(value, int | float) or value <= 0:
        return None
    return int(value)


def _positive_float(value: object) -> float | None:
    if not isinstance(value, int | float) or value <= 0:
        return None
    return float(value)
