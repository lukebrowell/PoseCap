# Task 0007: Acquire golden-sample ground-truth data

**Status:** proposed
**Created:** 2026-06-11
**Owner:** alexandremendoncaalvaro (synthetic) + Dean / Corridor (real session)
**Execution:** HITL
**Spec ref:**
**Board ref:**

## Context

The pose-accuracy eval harness (PRD Next roadmap) needs labeled data, and data acquisition has no code dependency — it can and should run in parallel with MVP development rather than after it. The real-session half has the longest scheduling lead time of anything on the roadmap because it depends on Corridor's calendar, not ours. Capturing early also upgrades task 0003's integration fixtures from synthetic-only to real labeled frames, and lets the engine be developed against real-world footage from day one. Ground-truth tiers per the PRD: synthetic renders are a perfect answer key; suit-plus-webcam is a high-quality real-world reference (suit exports live in the suit's own skeleton, so mapping to SMPL-X for comparison adds its own error — comparison method is the eval spike's problem); footage without a suit yields no true values (qualitative and jitter checks only). Whether Corridor has suit or other capture hardware is unconfirmed — the real-session half of this task is gated on Dean's answer. All data must be self-made — research datasets are license-restricted and never enter the repo.

## Acceptance Criteria

Verifiable conditions. Each as a checkbox so progress is point-editable.

- [ ] Synthetic set: at least 3 rendered SMPL-X animation clips with per-frame pose parameters saved alongside (the exact values used to drive the render), covering slow motion, fast motion, and partial occlusion.
- [ ] Synthetic clips are reproducible: source .blend plus render script committed; rendered frames generated locally, not committed (gitignore covers them).
- [ ] Capture-hardware reality check: Dean confirms what Corridor can access (mocap suit, optical system, multi-camera, or nothing); answer recorded in Notes and the real-session criteria below adjusted to match before any shoot is planned.
- [ ] Real session (gated on confirmed hardware): performer captured by the reference system while a webcam films simultaneously; reference export and webcam video stored as a synchronized pair with a documented sync method (clap/flash or timecode). If no reference hardware exists, this becomes a footage-only session for qualitative and jitter checks, documented as such.
- [ ] Real session covers an agreed move set (documented in Notes before the shoot): idle, walk-in-place, arm reaches, torso twists, one fast action.
- [ ] All captured data is Corridor/self-owned with no third-party license attached; storage location and access documented in Notes (large files stay out of the repo).
- [ ] A subset of labeled frames is packaged as task 0003 integration fixtures.

## Plan

Concrete sequential steps. Each as a checkbox. Reference file paths where applicable.

- [ ] Author the synthetic animation .blend driving the SMPL-X model with known parameters; export per-frame parameter JSON.
- [ ] `tools/render_golden.py` — deterministic render script (camera, lighting, resolution documented).
- [ ] Agree the real-session move set with Dean; record it in Notes.
- [ ] Corridor schedules and shoots the suit-plus-webcam session; deliverables: suit export (FBX/BVH), webcam video, sync marker.
- [ ] Verify sync and label quality; document storage location in Notes.
- [ ] Package the task 0003 fixture subset.

## Notes

Append-only log. Date each entry. Never rewrite past entries.

## Definition of Done

All Acceptance Criteria checked, plus:

- [ ] Local tests pass (or N/A documented in Notes)
- [ ] Code review completed (human or fresh-context reviewer per WORKFLOW §10)
- [ ] No orphan `TODO`/`FIXME` introduced
- [ ] Status updated to `done` and Notes log closes the task
