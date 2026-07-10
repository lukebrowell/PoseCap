from pathlib import Path

import numpy as np
import pytest
from posecap_engine.preview import PreviewFrameWriter


class _FakeCv2:
    COLOR_RGB2BGR = 4

    def __init__(self) -> None:
        self.written: list[str] = []
        self.resized: list[tuple[int, int]] = []

    def cvtColor(self, image, code):  # noqa: N802 - mirrors cv2 name
        return image

    def resize(self, image, size):
        self.resized.append(size)
        return np.zeros((size[1], size[0], 3), dtype=np.uint8)

    def imwrite(self, path: str, _image) -> bool:
        Path(path).write_bytes(b"jpeg")
        self.written.append(path)
        return True


def _frame(width: int, height: int) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


def test_writer_only_writes_every_interval_frame(tmp_path: Path) -> None:
    cv2 = _FakeCv2()
    writer = PreviewFrameWriter(tmp_path / "preview.jpg", cv2, interval=3, max_width=360)

    assert writer.offer(_frame(320, 240)) is False
    assert writer.offer(_frame(320, 240)) is False
    assert writer.offer(_frame(320, 240)) is True

    assert len(cv2.written) == 1
    assert (tmp_path / "preview.jpg").is_file()


def test_writer_downscales_wide_frames_keeping_aspect(tmp_path: Path) -> None:
    cv2 = _FakeCv2()
    writer = PreviewFrameWriter(tmp_path / "preview.jpg", cv2, interval=1, max_width=360)

    writer.offer(_frame(1280, 720))

    assert cv2.resized == [(360, 202)]


def test_writer_leaves_small_frames_untouched(tmp_path: Path) -> None:
    cv2 = _FakeCv2()
    writer = PreviewFrameWriter(tmp_path / "preview.jpg", cv2, interval=1, max_width=360)

    writer.offer(_frame(320, 240))

    assert cv2.resized == []


def test_writer_publishes_atomically_via_a_valid_image_temp(tmp_path: Path) -> None:
    cv2 = _FakeCv2()
    target = tmp_path / "preview.jpg"
    writer = PreviewFrameWriter(target, cv2, interval=1, max_width=360)

    writer.offer(_frame(320, 240))

    # cv2 picks the format from the extension, so the temp must stay an image.
    assert cv2.written[0].endswith(".jpg")
    assert cv2.written[0] != str(target)
    assert target.is_file()


def test_writer_skips_when_imwrite_fails_instead_of_crashing(tmp_path: Path) -> None:
    class _FailingCv2(_FakeCv2):
        def imwrite(self, path: str, _image) -> bool:
            return False  # cv2 signals failure by return value, not an exception

    writer = PreviewFrameWriter(tmp_path / "preview.jpg", _FailingCv2(), interval=1)

    assert writer.offer(_frame(320, 240)) is False
    assert not (tmp_path / "preview.jpg").exists()


def test_writer_rejects_nonpositive_interval(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="interval"):
        PreviewFrameWriter(tmp_path / "p.jpg", _FakeCv2(), interval=0)
