import json
import re
from io import StringIO
from pathlib import Path

from posecap_engine import PEAR_MODELS_REVISION, PEAR_REVISION
from posecap_engine.capture import CameraDevice
from posecap_engine.cli import run
from posecap_engine.errors import CaptureUnavailableError


def test_devices_command_prints_json_for_addon_dropdown(monkeypatch) -> None:
    monkeypatch.setattr(
        "posecap_engine.capture.enumerate_devices",
        lambda max_index: [
            CameraDevice(index=max_index, name="Camera X", width=None, height=None, fps=None)
        ],
    )
    stdout = StringIO()
    stderr = StringIO()

    code = run(["devices", "--max-index", "3"], stdout=stdout, stderr=stderr)

    assert code == 0
    assert stderr.getvalue() == ""
    assert json.loads(stdout.getvalue()) == {
        "devices": [{"index": 3, "name": "Camera X", "width": None, "height": None, "fps": None}]
    }


def test_devices_command_reports_unavailable_capture_as_empty_list(monkeypatch) -> None:
    def unavailable(max_index: int) -> list[CameraDevice]:
        raise CaptureUnavailableError(f"no capture backend up to {max_index}")

    monkeypatch.setattr("posecap_engine.capture.enumerate_devices", unavailable)
    stdout = StringIO()
    stderr = StringIO()

    code = run(["devices", "--max-index", "1"], stdout=stdout, stderr=stderr)

    assert code == 0
    assert stderr.getvalue() == ""
    assert json.loads(stdout.getvalue()) == {
        "devices": [],
        "error": "no capture backend up to 1",
    }


def test_live_command_requires_fixture_or_pear_root() -> None:
    stdout = StringIO()
    stderr = StringIO()

    code = run(["live"], stdout=stdout, stderr=stderr)

    assert code == 1
    assert "live requires either --fixture or --pear-root" in stderr.getvalue()


def test_live_command_passes_pear_options_to_frame_source(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakePearFrameSource:
        def __init__(
            self,
            pear_root: Path,
            *,
            camera_index: int,
            width: int,
            height: int,
            yolo_threshold: float,
            crop_ratio: float,
        ) -> None:
            captured["source"] = {
                "pear_root": pear_root,
                "camera_index": camera_index,
                "width": width,
                "height": height,
                "yolo_threshold": yolo_threshold,
                "crop_ratio": crop_ratio,
            }

        def frames(self):
            return iter(())

    monkeypatch.setattr("posecap_engine.cli.PearFrameSource", FakePearFrameSource)
    monkeypatch.setattr("posecap_engine.cli.serve_once", lambda frames, **kwargs: None)
    stdout = StringIO()
    stderr = StringIO()

    code = run(
        [
            "live",
            "--pear-root",
            "C:/PEAR",
            "--camera-index",
            "4",
            "--width",
            "640",
            "--height",
            "480",
            "--yolo-threshold",
            "0.45",
            "--crop-ratio",
            "1.5",
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 0
    assert stderr.getvalue() == ""
    assert captured["source"] == {
        "pear_root": Path("C:/PEAR"),
        "camera_index": 4,
        "width": 640,
        "height": 480,
        "yolo_threshold": 0.45,
        "crop_ratio": 1.5,
    }


def test_doctor_command_prints_json_and_returns_error_code(monkeypatch) -> None:
    monkeypatch.setattr(
        "posecap_engine.cli.run_doctor",
        lambda **_kwargs: {
            "ok": False,
            "pear_root": None,
            "checks": [
                {"name": "torch_cuda", "status": "error", "message": "missing", "details": {}}
            ],
        },
    )
    stdout = StringIO()
    stderr = StringIO()

    code = run(["doctor"], stdout=stdout, stderr=stderr)

    assert code == 1
    assert stderr.getvalue() == ""
    assert json.loads(stdout.getvalue()) == {
        "ok": False,
        "pear_root": None,
        "checks": [{"name": "torch_cuda", "status": "error", "message": "missing", "details": {}}],
    }


def test_external_pear_pins_are_full_commit_shas() -> None:
    assert re.fullmatch(r"[0-9a-f]{40}", PEAR_REVISION)
    assert re.fullmatch(r"[0-9a-f]{40}", PEAR_MODELS_REVISION)
