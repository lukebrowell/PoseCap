"""Record Live MoCap start/stop operators.

Recording lays down `rotation_quaternion` keyframes for every applied stream
frame at the advancing playhead. The playhead only advances while the timeline
is playing, so start begins playback and stop pauses it — otherwise every key
would pile onto a single frame. The `record_live_mocap` scene flag is the single
source of truth the apply timer reads live each tick (decoupled from any preview
setting — spec R6).
"""

from __future__ import annotations

from typing import Any


def build_recording_classes(bpy_module: Any) -> tuple[type[Any], ...]:
    """Build the recording operator classes against a bpy-like module."""

    class POSECAP_OT_StartRecording(bpy_module.types.Operator):
        bl_idname = "posecap.start_recording"
        bl_label = "Record Live MoCap"
        bl_description = "Start laying down keyframes at the advancing playhead"
        bl_options = {"REGISTER"}

        def execute(self, context: Any) -> set[str]:
            return _start_recording(context, bpy_module)

    class POSECAP_OT_StopRecording(bpy_module.types.Operator):
        bl_idname = "posecap.stop_recording"
        bl_label = "Stop Recording"
        bl_description = "Stop recording keyframes and pause the timeline"
        bl_options = {"REGISTER"}

        def execute(self, context: Any) -> set[str]:
            return _stop_recording(context, bpy_module)

    return (POSECAP_OT_StartRecording, POSECAP_OT_StopRecording)


def _start_recording(context: Any, bpy_module: Any) -> set[str]:
    settings = context.scene.posecap
    settings.record_live_mocap = True
    settings.lifecycle_state = "RECORDING"
    settings.status_message = "Recording"
    _set_animation_playing(context, bpy_module, playing=True)
    return {"FINISHED"}


def _stop_recording(context: Any, bpy_module: Any) -> set[str]:
    settings = context.scene.posecap
    settings.record_live_mocap = False
    settings.lifecycle_state = "STREAMING"
    settings.status_message = "Streaming"
    _set_animation_playing(context, bpy_module, playing=False)
    return {"FINISHED"}


def _set_animation_playing(context: Any, bpy_module: Any, *, playing: bool) -> None:
    """Toggle timeline playback idempotently.

    `screen.animation_play` is a toggle, so guard on `is_animation_playing` —
    calling it while already in the desired state would flip the wrong way and
    orphan keys on rapid Record on/off cycles.
    """
    screen = getattr(context, "screen", None)
    is_playing = bool(getattr(screen, "is_animation_playing", False))
    if playing and not is_playing:
        bpy_module.ops.screen.animation_play()
        return
    if not playing and is_playing:
        bpy_module.ops.screen.animation_cancel(restore_frame=False)
