"""Side-channel preview frames for the live UI.

This is NOT the pose wire format — it is an operational artifact (like the
log): the engine drops the current camera/video frame as a small JPEG so the
addon can show a live thumbnail in the panel during streaming. Works the same
for a webcam and a video file because both flow through the one read path.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class PreviewFrameWriter:
    """Publish every Nth frame as a downscaled JPEG, written atomically."""

    def __init__(
        self,
        path: Path,
        cv2: Any,
        *,
        interval: int = 6,
        max_width: int = 360,
    ) -> None:
        if interval <= 0:
            raise ValueError("interval must be positive")
        self._path = Path(path)
        self._cv2 = cv2
        self._interval = interval
        self._max_width = max_width
        self._count = 0

    def offer(self, rgb_image: Any) -> bool:
        """Publish the frame if it lands on the interval; return whether it wrote."""
        self._count += 1
        if self._count % self._interval != 0:
            return False
        self._write(rgb_image)
        return True

    def _write(self, rgb_image: Any) -> None:
        image = self._downscale(rgb_image)
        bgr = self._cv2.cvtColor(image, self._cv2.COLOR_RGB2BGR)
        temporary = self._path.with_name(self._path.name + ".tmp")
        self._cv2.imwrite(str(temporary), bgr)
        os.replace(temporary, self._path)

    def _downscale(self, rgb_image: Any) -> Any:
        height, width = rgb_image.shape[:2]
        if width <= self._max_width:
            return rgb_image
        scale = self._max_width / float(width)
        return self._cv2.resize(rgb_image, (self._max_width, max(1, int(height * scale))))
