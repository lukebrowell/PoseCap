# Task 0003: Engine bridge — TCP pose server wrapping PEAR

**Status:** in progress
**Created:** 2026-06-11
**Owner:** alexandremendoncaalvaro
**Execution:** HITL
**Spec ref:** doc/specs/0001-live-webcam-pose-streaming.md
**Board ref:**

## Context

The engine side reuses the POC's verified inference loop (`PEAR/live_webcam.py:146-209`: capture without CAP_DSHOW — it froze some Windows webcams; YOLO classes=0 imgsz=640 most-confident box; crop-ratio patch; torch.no_grad; cv2.Rodrigues conversion) and replaces the pickle/os.replace file handoff with NDJSON over a localhost TCP server (ADR-0002/0003). PEAR installs from a pinned external revision (ADR-0005); weights pin a HuggingFace revision with `weights_only=True` — the POC's global `torch.load` monkeypatch (`live_webcam.py:13`) is banned. Device enumeration moves here because the engine owns the environment that can enumerate (the POC's in-Blender attempt never worked). The spec's open question on TCP port strategy gets resolved and recorded in this task's Notes. HITL: needs CUDA GPU and a physical webcam. Depends on tasks 0001-0002.

## Acceptance Criteria

Verifiable conditions. Each as a checkbox so progress is point-editable.

- [x] `uv run posecap-engine devices` prints a JSON device list usable by the addon dropdown.
- [ ] Live mode serves schema-valid NDJSON pose frames at inference rate; "no person" produces explicit status frames, not silence.
- [x] Integration test against recorded fixture frames (no live camera) validates frames against the golden schema; `gpu` tag skips cleanly without CUDA.
- [x] Engine exits within 5 seconds of parent-PID death and on stream-socket disconnect (decision between the two recorded in Notes).
- [x] PEAR revision and HF weight revision pinned in config; no `weights_only=False` anywhere (grep-clean).
- [x] Inference FPS logged at INFO on an interval to a rotating log; no per-frame disk I/O or above-DEBUG logging on the hot path.
- [x] TCP port strategy implemented and documented (Notes + contracts handshake if schema changed).

## Plan

Concrete sequential steps. Each as a checkbox. Reference file paths where applicable.

- [x] `engine/src/posecap_engine/capture.py` — webcam open/read (no CAP_DSHOW), device enumeration.
- [ ] `engine/src/posecap_engine/pear_adapter.py` — model load (pinned), detect+infer+Rodrigues, reusing POC loop structure.
- [x] `engine/src/posecap_engine/stream_server.py` — TCP server, NDJSON frames via contracts codec, single-client lifecycle.
- [x] `engine/src/posecap_engine/watchdog.py` — parent-PID + disconnect liveness (platform adapter).
- [x] `engine/src/posecap_engine/cli.py` — `devices` and `live` entry points.
- [x] Resolve port strategy; record in Notes; update contracts if handshake needed.
- [x] `tests/engine/` — fixture-frame integration tests (`integration`/`gpu` tags).
- [ ] Full gate + /ad-commit.

## Notes

Append-only log. Date each entry. Never rewrite past entries.

### 2026-06-11

Decision: the recorded-frame fixtures created for this task's integration tests carry ground-truth pose labels (rendered SMPL-X sequences with known parameters) so the pose-accuracy eval harness (PRD Next roadmap) has labeled data from day one. The harness itself is out of this task's scope — it gets its own spike after the engine CLI lands.

### 2026-06-27

Started the non-GPU engine slice: `posecap-engine devices`, `posecap-engine live --fixture`, single-client localhost TCP NDJSON streaming via the contracts codec, parent-process watchdog, socket-disconnect shutdown, rotating-log setup, and pinned PEAR / HF model revisions. PEAR inference itself remains unchecked until the external checkout, model weights, CUDA, and physical webcam are available.

Port strategy decision: `live` defaults to TCP port `0`, letting the OS allocate a free localhost port. The engine prints one startup JSON line to stdout with `{"event":"listening","host":"127.0.0.1","port":<actual>}`; the addon will read that line from the spawned process before connecting. No wire-contract handshake changed: pose frames on the socket remain newline-delimited JSON `PoseFrame` lines.

Liveness decision: both parent-PID death and client disconnect are implemented. The accept loop polls the parent watchdog; the stream loop checks parent liveness before each frame and exits when the client sends FIN/RST.

Local verification added for the engine checkpoint: `devices` emits a JSON object even when OpenCV is absent, fixture streaming decodes through `posecap_contracts`, empty fixtures fail explicitly instead of spinning, the FPS logger emits only after its interval, and the `gpu` smoke skips cleanly without `torch` or CUDA. The PEAR adapter now validates the external checkout boundary before reporting that CUDA/HITL inference remains incomplete.

OpenCV is now an engine dependency so `uv run posecap-engine devices` can enumerate from a normal `uv sync`; on this workstation `--max-index 0` returned Camera 0 at 1280x720 and 60 FPS. The command still emits a JSON object with an empty list plus `error` if the capture backend is unavailable.

## Definition of Done

All Acceptance Criteria checked, plus:

- [ ] Local tests pass (or N/A documented in Notes)
- [ ] Code review completed (human or fresh-context reviewer per WORKFLOW §10)
- [ ] No orphan `TODO`/`FIXME` introduced
- [ ] Status updated to `done` and Notes log closes the task
