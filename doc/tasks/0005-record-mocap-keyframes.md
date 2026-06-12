# Task 0005: Record Live MoCap and keyframe manager

**Status:** proposed
**Created:** 2026-06-11
**Owner:** alexandremendoncaalvaro
**Execution:** HITL
**Spec ref:** doc/specs/0001-live-webcam-pose-streaming.md
**Board ref:**

## Context

Recording is the POC's most dangerous trap fixed: keyframe insertion was nested inside the preview branch (`operators/pose.py:822-827`), so recording silently captured nothing with preview off — spec R6 decouples them. Keyframes insert on `rotation_quaternion` only (POC contract, `operators/pose.py:142-171`); start/stop sync to timeline playback (`operators/pose.py:940-970`). The Blender 5.x fcurve access fallback (`action.fcurves` vs `action_slot`+channelbag) appears twice verbatim in the POC (`operators/keyframes.py:84-97`, `174-185`) — it becomes one helper. Keyframe persistence across restarts is spec R7 with a POC-verified no-clear guarantee to preserve. The keyframe manager (add/remove/clear/add-all/bake-and-retain) is a verified-working POC feature in parity scope. The spec's open question on recording density (per streamed frame vs scene-frame resample) is resolved here with a test. Depends on task 0004.

## Acceptance Criteria

Verifiable conditions. Each as a checkbox so progress is point-editable.

- [ ] Record toggle inserts keyframes at the advancing playhead while streaming with preview ON and with preview OFF (both verified).
- [ ] Record start begins timeline playback; stop ends it and finalizes; rapid on/off cycles produce no duplicate or orphaned keys.
- [ ] Five consecutive stream restarts lose zero pre-existing keyframes (automated count, spec success criterion).
- [ ] Keyframe manager operators ported (add, remove, clear, add all active, bake and retain) using a single shared 5.x-compatible fcurves helper; verified on 4.2 and 5.x.
- [ ] Recording-density decision (per streamed frame vs resample) made, tested, and recorded in Notes.
- [ ] A recording session's keys match applied frames at correct playhead positions within scene-FPS granularity (e2e check, spec success criterion).

## Plan

Concrete sequential steps. Each as a checkbox. Reference file paths where applicable.

- [ ] `core/` keyframe policy: recording flag independent of preview; which bones/paths get keys.
- [ ] `addon/.../keyframe_io.py` — single 5.x-compatible fcurves helper (action_slot/channelbag fallback).
- [ ] `addon/.../recording.py` — start/stop operators, playback sync, insertion at playhead.
- [ ] Keyframe manager operators + UI list port.
- [ ] Resolve density question with a comparative test; Notes entry.
- [ ] Automated restart-persistence and key-position e2e checks.
- [ ] Full gate + /ad-commit.

## Notes

Append-only log. Date each entry. Never rewrite past entries.

## Definition of Done

All Acceptance Criteria checked, plus:

- [ ] Local tests pass (or N/A documented in Notes)
- [ ] Code review completed (human or fresh-context reviewer per WORKFLOW §10)
- [ ] No orphan `TODO`/`FIXME` introduced
- [ ] Status updated to `done` and Notes log closes the task
