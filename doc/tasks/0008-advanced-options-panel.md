# Task 0008: Advanced options — CK2P-style progressive disclosure

**Status:** proposed
**Created:** 2026-07-10
**Owner:** alexandremendoncaalvaro
**Execution:** agent + HITL (UI review)
**Spec ref:** doc/specs/0001-live-webcam-pose-streaming.md
**Board ref:**

## Context

Product principle (Ale, 2026-07-10): main flow stays simple and automated, but
everything sensible is parametrizable behind an expandable Advanced section —
the CK2P interface model. Grounded against comparable markerless-mocap tools:
Rokoko Studio Live exposes retarget bone-mapping + auto-scale
(github.com/Rokoko/rokoko-studio-live-blender); DeepMotion Animate 3D exposes
foot locking, physics/stabilization filters, hand/face toggles; Move AI ships
temporal smoothing + biomechanical constraints; Autodesk Flow Studio exposes
custom rigs, auto-retargeting, foot locking, smoothing. Their common surface is
the user-expectation baseline.

Already parametrizable in PoseCap internals but not exposed in the UI:
One Euro smoothing (`min_cutoff`, `beta` — core `PoseSmoother`, panel has only
the toggle), YOLO confidence threshold + detector model + capture resolution
(`PearLiveConfig`), rig-converter knobs (CLI only: mapping JSON, bone length,
probe tolerance).

## Acceptance Criteria

- [ ] Panel gains a collapsed "Advanced" sub-section (default closed); the
      basic flow is visually unchanged when collapsed.
- [ ] Smoothing exposes Min Cutoff (Hz) and Beta sliders under Advanced,
      defaults 1.0 / 0.5, live-applied on next Start Stream; tooltips state
      the Casiez semantics (lower cutoff = calmer at rest; higher beta =
      less lag on fast moves).
- [ ] Engine settings exposed under Advanced: detection confidence
      (yolo_threshold), detector model (yolov8s/yolov8x enum), capture
      resolution — passed through the engine CLI by Start Stream.
- [ ] Every advanced property has a sane default equal to today's hardcoded
      value; a fresh scene behaves identically to pre-task builds.
- [ ] Rig converter is a one-click panel operator ("Convert Rig for PoseCap":
      pick armature → convert → report probe result in the UI). The CLI in
      tools/convert_target_armature.py is internal plumbing only — the user
      NEVER touches a terminal (PRD: target user is an animator on a machine
      without dev tooling; binding directive Ale 2026-07-10).
- [ ] Candidate list for future options recorded in Notes with the grounding
      source for each (foot lock, physics filter, per-limb confidence gating).

## Plan

- [ ] Panel Advanced sub-section scaffold (collapsed `layout.panel` /
      `use_property_split` per Blender 4.2+ UI conventions).
- [ ] Scene properties + wiring for smoothing sliders → `PoseSmoother` kwargs.
- [ ] Scene properties + engine-command flags for yolo_threshold / model /
      resolution (engine CLI already accepts config; verify flags exist,
      add if missing).
- [ ] TDD per behavior (panel draw, prop registration, Start Stream command
      assembly) following tests/addon/test_ui_state.py patterns.
- [ ] HITL pass: screenshot of collapsed vs expanded panel for Ale.

## Notes

Append-only log. Date each entry. Never rewrite past entries.

### 2026-07-10

Task created from the parametrization principle + tool-comparison ground.

Binding product directive (Ale, same day): PoseCap users are video editors,
animators and designers — not tech experts. Nothing user-facing may depend on
a command line or a separate library install; every capability ships as GUI
(panel operator or installer step). The rig converter AC above was hardened
accordingly: the tools/ CLI is dev/CI plumbing, the user path is a one-click
operator. This directive also re-scopes how future options land: always
panel-first.
Future-option candidates (not in scope here): foot lock / foot planting
(DeepMotion, Move AI, Autodesk Flow all ship it — needs contact detection),
physics/stabilization filter (DeepMotion), per-joint confidence gating
(hold last pose when PEAR confidence drops), hand/face apply toggles
(SMPL-X hand poses already stream; face/jaw unused).

## Definition of Done

All Acceptance Criteria checked, plus:

- [ ] Local tests pass (or N/A documented in Notes)
- [ ] Code review completed (human or fresh-context reviewer per WORKFLOW §10)
- [ ] No orphan `TODO`/`FIXME` introduced
- [ ] Status updated to `done` and Notes log closes the task
