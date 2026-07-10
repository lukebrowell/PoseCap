# Task 0009: Stream reader must drain — latest-wins at the transport layer

**Status:** proposed
**Created:** 2026-07-10
**Owner:** alexandremendoncaalvaro
**Execution:** agent
**Spec ref:** doc/specs/0001-live-webcam-pose-streaming.md
**Board ref:**

## Context

Found during the 2026-07-10 character demos: with a heavy viewport (EEVEE
Material Preview), applied poses lagged the engine's emission by ~4 seconds —
"totally desynchronized" to the eye — while the same scene under Solid shading
tracked exactly. Mechanism: `TcpPoseStreamClient._read_frames` reads ONE line
per loop iteration; the reader daemon thread competes with Blender's busy main
thread for the GIL, falls below the engine's emission rate, and TCP
backpressure turns the OS socket buffers (~tens of NDJSON frames) into a FIFO
delay line. The latest-wins slot then holds "the newest line the reader got
to", not "the newest frame the engine produced". Lightweight viewports mask
the bug; heavy viewports (or slower machines — Dean's) will hit it in real
camera use.

Evidence: dp_rec5 vs dp_rec6 instrumented takes (tee proxy logging emission
wall-times; sit-window alignment check) — same scene, only shading differed.

## Acceptance Criteria

- [ ] When the reader thread is artificially slowed (test-controlled), the
      frame returned by `latest()` is never older than the newest COMPLETE
      frame available on the socket at read time (bounded by one read cycle).
- [ ] Under a normal-speed reader, behavior is unchanged (existing stream
      client tests stay green).
- [ ] Reconnect / EOF / decode-error semantics unchanged.
- [ ] Apply-time instrumentation (or a new counter) exposes dropped-by-drain
      frame counts at DEBUG so lag like this is observable in the log.

## Plan

- [ ] TDD: regression test with a slow consumer and a fast producer asserting
      the applied frame's seq is near the newest written seq.
- [ ] Rework `_read_frames` to drain all complete lines available on the
      socket per wake-up (non-blocking recv into a buffer, split lines, keep
      newest) instead of one blocking `readline()` per frame.
- [ ] Full gates + fresh-context review per WORKFLOW §10.

## Notes

Append-only log. Date each entry. Never rewrite past entries.

### 2026-07-10

Created from the demo desync investigation. Workaround used for the demo:
lightweight viewport settings (Material Preview with `taa_samples=1`, studio
light) keep the reader ahead of the stream; verified visually on 5 checkpoint
frames. The product fix removes the workaround's necessity.

### 2026-07-10 (fix built, v0.1.3 slice)

`_read_frames` reworked: blocking `recv` for the first chunk, then a
non-blocking drain of everything already queued on the socket, then decode
of only the newest complete line (partial tail kept across wake-ups).
Dropped-frame count exposed as `frames_dropped_by_drain` and logged at
DEBUG. Regression test slows the decoder artificially (25 ms per decode,
50 fast frames): the FIFO reader needs >1.2 s to reach the newest frame,
the draining reader a handful of cycles — asserted under 0.8 s, 5/5 runs
stable locally. Existing reconnect / idle-gap / EOF / close tests stayed
green untouched.

`/ad-review` (Spec axis) noted a deliberate deviation from AC "decode-error
semantics unchanged": intermediate frames superseded within one drain batch
are dropped before `decode_pose_frame`, so a corrupt frame that a newer
frame immediately supersedes no longer raises. This is inherent to
latest-wins draining (decoding every stale frame would reintroduce the very
per-frame cost the fix removes) and is accepted: the newest frame is always
decoded, so a persistent decode fault still surfaces on the next cycle;
transient corruption on a superseded frame is correctly irrelevant.

## Definition of Done

All Acceptance Criteria checked, plus:

- [ ] Local tests pass (or N/A documented in Notes)
- [ ] Code review completed (human or fresh-context reviewer per WORKFLOW §10)
- [ ] No orphan `TODO`/`FIXME` introduced
- [ ] Status updated to `done` and Notes log closes the task
