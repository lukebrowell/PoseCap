"""Behavior tests for the Record Live MoCap start/stop operators.

Recording is toggled during an active stream: start lays down keyframes at the
advancing playhead (so it must start timeline playback), stop finalizes and
pauses. The flag and lifecycle transitions are pure enough to test with fakes;
the actual `screen.animation_play` call is verified HITL in Blender.
"""

from __future__ import annotations

from types import SimpleNamespace

from posecap_addon.recording import build_recording_classes


class _Screen:
    def __init__(self, *, is_playing: bool) -> None:
        self.is_animation_playing = is_playing


class _PlaybackOps:
    """Stand-in for bpy.ops.screen.{animation_play,animation_cancel}."""

    def __init__(self, screen: _Screen) -> None:
        self._screen = screen
        self.calls: list[str] = []

    def animation_play(self, *_args: object, **_kwargs: object) -> set[str]:
        self.calls.append("play")
        self._screen.is_animation_playing = True
        return {"FINISHED"}

    def animation_cancel(self, *_args: object, **kwargs: object) -> set[str]:
        self.calls.append(f"cancel:restore={kwargs.get('restore_frame')}")
        self._screen.is_animation_playing = False
        return {"FINISHED"}


def _fake_bpy(screen: _Screen) -> tuple[SimpleNamespace, _PlaybackOps]:
    playback = _PlaybackOps(screen)
    bpy_module = SimpleNamespace(
        types=SimpleNamespace(Operator=object),
        ops=SimpleNamespace(screen=playback),
    )
    return bpy_module, playback


def _settings(*, lifecycle_state: str) -> SimpleNamespace:
    return SimpleNamespace(
        lifecycle_state=lifecycle_state,
        status_message="",
        record_live_mocap=False,
    )


def _context(settings: SimpleNamespace, screen: _Screen) -> SimpleNamespace:
    return SimpleNamespace(scene=SimpleNamespace(posecap=settings), screen=screen)


def test_start_recording_sets_flag_enters_recording_and_starts_playback() -> None:
    settings = _settings(lifecycle_state="STREAMING")
    screen = _Screen(is_playing=False)
    bpy_module, playback = _fake_bpy(screen)
    start_cls, _stop_cls = build_recording_classes(bpy_module)

    result = start_cls().execute(_context(settings, screen))

    assert result == {"FINISHED"}
    assert settings.record_live_mocap is True
    assert settings.lifecycle_state == "RECORDING"
    assert playback.calls == ["play"]


def test_stop_recording_clears_flag_returns_to_streaming_and_pauses() -> None:
    settings = _settings(lifecycle_state="RECORDING")
    settings.record_live_mocap = True
    screen = _Screen(is_playing=True)
    bpy_module, playback = _fake_bpy(screen)
    _start_cls, stop_cls = build_recording_classes(bpy_module)

    result = stop_cls().execute(_context(settings, screen))

    assert result == {"FINISHED"}
    assert settings.record_live_mocap is False
    assert settings.lifecycle_state == "STREAMING"
    assert playback.calls == ["cancel:restore=False"]


def test_start_recording_does_not_double_start_playback_when_already_playing() -> None:
    settings = _settings(lifecycle_state="STREAMING")
    screen = _Screen(is_playing=True)
    bpy_module, playback = _fake_bpy(screen)
    start_cls, _stop_cls = build_recording_classes(bpy_module)

    start_cls().execute(_context(settings, screen))

    assert settings.record_live_mocap is True
    assert playback.calls == []


def test_stop_recording_does_not_cancel_playback_when_already_paused() -> None:
    settings = _settings(lifecycle_state="RECORDING")
    settings.record_live_mocap = True
    screen = _Screen(is_playing=False)
    bpy_module, playback = _fake_bpy(screen)
    _start_cls, stop_cls = build_recording_classes(bpy_module)

    stop_cls().execute(_context(settings, screen))

    assert settings.record_live_mocap is False
    assert playback.calls == []
