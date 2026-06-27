from pathlib import Path

import pytest
from posecap_engine.errors import CaptureUnavailableError
from posecap_engine.pear_adapter import PearFrameSource


def test_pear_frame_source_reports_missing_external_checkout(tmp_path: Path) -> None:
    source = PearFrameSource(tmp_path / "missing-pear", camera_index=0)

    with pytest.raises(CaptureUnavailableError, match="PEAR checkout not found"):
        source.frames()
