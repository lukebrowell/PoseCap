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
- [ ] Converter auto-detects the skeleton family from bone names (UE and
      Mixamo presets ship; Mixamo unlocks Adobe's free character library) and
      supports a custom mapping; conversion runs in the OPEN file as a native
      undoable operator — no subprocess, no terminal, Ctrl+Z reverts.
- [ ] Per-limb apply filters (core LimbFilter, already tested) exposed as
      simple checkboxes (arms / legs / torso) — apply capture to part of the
      body only.
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

Release slice decided (Ale, 2026-07-10 evening, after sending v0.1.2 to Dean):
the next significant release (v0.1.3) bundles the REMAINDER of this task —
Character Setup panel section (one-click converter, UE + Mixamo auto-detect,
undoable), engine parameters under Advanced (detection confidence,
quality/speed detector dropdown, capture resolution), per-limb filters —
PLUS task 0009 (stream reader drain, removes the heavy-viewport known issue
before Dean hits it). Smoothing toggle + sliders already shipped in v0.1.2.

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

### 2026-07-10 (remainder built, v0.1.3 slice)

Character Setup: the proven converter engine moved from tools/ into
`addon/posecap_addon/character_setup.py` (the extension must ship it; the
addon cannot import tools/ at runtime); `sys.exit` calls became
`ConversionError` with user-facing messages; tools CLI is now a thin shim
over the same module, its test surface unchanged. Mixamo preset grounded on
the rebocap SDK mixamorig↔SMPL table (index-aligned; Spine/Spine1/Spine2 →
spine1/2/3, LeftToeBase → left_foot) with prefix auto-detect by regex
(mpfb2 finding: prefix varies — `mixamorig:`, numbered, or stripped).
Mixamo characters download in T-pose, so their preset skips the UE-style
A-pose re-rest. Operator `posecap.convert_character` is native and undoable
(REGISTER | UNDO), reports the probe error in the UI, supports custom
mapping JSON.

Engine params: the CLI already exposed --yolo-threshold/--yolo-model/
--width/--height (handoff doubt resolved — no engine change needed); the
Advanced section gained detection confidence, detector dropdown (n/s/m/x,
labeled by speed/quality) and capture resolution, all passed by Start
Stream, defaults equal to the previous hardcoded values.

Per-limb filters: core `LimbFilter` gained a `torso` group (spine chain,
neck, head, collars — pelvis stays excluded when filtering, POC semantics)
so the three checkboxes (Arms / Legs / Torso, all on by default = no
filtering) can express every combination; wired into `PoseApplyTimer`.

`/ad-review` follow-ups applied before release: (1) unchecking all three
limb boxes now applies NOTHING (core `LimbFilter.apply_nothing`, empty
whitelist) instead of silently driving the whole body — the all-False
default still means "no filter"; (2) the retarget engine's placement in
addon/ (vs core/ per ARCHITECTURE.md) and the `axis_angle_quaternion`
duplication are logged as task 0011 (deferred: justified by the stdlib-only
dev-CLI constraint, not a release blocker).

Open: HITL screenshot pass of collapsed vs expanded panel for Ale.

## Definition of Done

All Acceptance Criteria checked, plus:

- [ ] Local tests pass (or N/A documented in Notes)
- [ ] Code review completed (human or fresh-context reviewer per WORKFLOW §10)
- [ ] No orphan `TODO`/`FIXME` introduced
- [ ] Status updated to `done` and Notes log closes the task
