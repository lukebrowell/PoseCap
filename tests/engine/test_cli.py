import json
import re
from io import StringIO

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


def test_external_pear_pins_are_full_commit_shas() -> None:
    assert re.fullmatch(r"[0-9a-f]{40}", PEAR_REVISION)
    assert re.fullmatch(r"[0-9a-f]{40}", PEAR_MODELS_REVISION)
