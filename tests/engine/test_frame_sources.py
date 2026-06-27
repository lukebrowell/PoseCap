from pathlib import Path

import pytest
from posecap_engine.errors import EngineError
from posecap_engine.frame_sources import FixtureFrameSource


def test_fixture_frame_source_rejects_empty_file(tmp_path: Path) -> None:
    fixture = tmp_path / "empty.ndjson"
    fixture.write_text("\n", encoding="utf-8")

    source = FixtureFrameSource(fixture, repeat=True)

    with pytest.raises(EngineError, match="fixture contains no pose frames"):
        list(source.frames())
