"""Lazy PEAR adapter boundary.

PEAR stays external and pinned by config; importing this module must not import
torch, OpenCV, or upstream PEAR.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from posecap_contracts import PoseFrame

from .config import (
    PEAR_MODELS_REPOSITORY_URL,
    PEAR_MODELS_REVISION,
    PEAR_REPOSITORY_URL,
    PEAR_REVISION,
)
from .errors import CaptureUnavailableError


@dataclass(frozen=True)
class PearLiveConfig:
    """Runtime settings for PEAR live inference."""

    pear_root: Path
    camera_index: int
    width: int = 1280
    height: int = 720
    yolo_threshold: float = 0.25
    crop_ratio: float = 1.25


class PearFrameSource:
    """Frame source for the external PEAR checkout."""

    def __init__(self, pear_root: Path, *, camera_index: int) -> None:
        self._config = PearLiveConfig(pear_root=pear_root, camera_index=camera_index)

    def frames(self) -> Iterator[PoseFrame]:
        _validate_external_checkout(self._config.pear_root)
        raise CaptureUnavailableError(
            "PEAR live inference requires the CUDA/HITL adapter to be completed. "
            f"Expected PEAR {PEAR_REPOSITORY_URL}@{PEAR_REVISION} and weights "
            f"{PEAR_MODELS_REPOSITORY_URL}@{PEAR_MODELS_REVISION}; "
            f"camera index {self._config.camera_index}, root {self._config.pear_root}."
        )


def _validate_external_checkout(pear_root: Path) -> None:
    if not pear_root.exists():
        raise CaptureUnavailableError(f"PEAR checkout not found: {pear_root}")
    if not pear_root.is_dir():
        raise CaptureUnavailableError(f"PEAR checkout is not a directory: {pear_root}")
    if not (pear_root / "models").exists():
        raise CaptureUnavailableError(
            f"PEAR checkout missing expected models package: {pear_root / 'models'}"
        )
