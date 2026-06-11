# POC Verification Report

Evidence-based audit of `C:\Dev\CorridorRig-Original`: which features verifiably work, which are code-complete but unproven, and which Dean tried and abandoned. This file is the canonical source for the MVP parity checklist — the PRD scopes parity against the "verified working" and "code-complete" tiers, not against the POC's README claims.

Method: UI reachability tracing (panel button to registered operator), runtime artifact forensics (output files, timestamps, 54,014-line modal log), feature-spec completion check, and claims-vs-code comparison.

## Verified working — ran successfully, artifacts prove it

| Feature | Evidence |
|---|---|
| Live webcam stream | 3 sessions logged (modal_log.txt, 2.5 MB): 2 on June 1 (24.7% error rate), 1 on June 8 — 10.6 min, zero errors, 20,329 successful pose loads. `live_pose.pkl` mtime matches last log line. |
| Single timed capture | `capture_1780964418.jpg` + `.pkl` pair; ~9 s capture-to-pose end to end. |
| Batch image upload | Two proven runs (`batch_upload_1780961954`, `batch_upload_1780968045`), 3 pose files each. |
| SMPL-X v1.1 rig spawn | Full registration chain + bundled blend present; every streaming session required a spawned rig. |
| Pose import (.pkl) + per-limb filters + orientation fix | Shared loader proven by 20k+ live loads; import filter and flip props wired. |
| Keyframe manager (key poses, bake and retain) | All five operators registered and panel-wired; auto-invoked by every proven keyframed load. |
| Keyframe persistence on stream restart | Code-verified: no animation-data clearing exists anywhere in the start/restart path; insert-only semantics. |
| Webcam device index selection | `--webcam_index` passed in the proven capture and stream runs. |

## Code-complete, execution unproven — keep, but verify during rewrite

| Feature | Caveat |
|---|---|
| Record Live MoCap | Registered, wired, ran on stream sessions — but keyframes live only in .blend files, no artifact proves a recording. Trap: insertion is nested inside the Preview branch — recording silently no-ops when Preview Live Stream is off. Rate is bounded by inference throughput, not scene FPS. |
| Arduino serial input chain | Complete end to end (8-channel firmware, per-axis map/scale/flip/offset, vendored pyserial, full panel) and matches the feature spec — but zero on-disk artifacts prove a hardware session ever ran. |
| Photo upload (single image) | Built, registered, panel-wired, same backend as proven batch — no `upload_*` artifact anywhere; Dean never tested this button. |
| Load animation sequence | Registered and wired; shares the proven loader; no distinguishing artifact. |

## Broken — present but does not work as shipped

| Feature | Failure |
|---|---|
| Folder watcher | Dean's last experiment (built June 8 20:27). The only test image dropped at 22:25 produced no output, though the same image succeeded via batch upload 5 minutes earlier. Only mode with a dedicated launcher; only mode with zero success artifacts. |
| Webcam device-name dropdown | Enumeration shells to a `.venv` that does not exist and `pygrabber` is in no requirements file — silently falls back to generic "Camera 0-4". Index selection works; name resolution never did. |
| Live stream object-lifetime fragility | 6,670 "StructRNA of type Object has been removed" errors on June 1 — the modal loop kept dereferencing a deleted armature. June 8 ran clean, but no code guards the reference; the rewrite must validate per frame. |
| Texture operator | Registered, textures bundled (73 MB), no panel exposes it — F3-only orphan. |
| Shape editing suite (measurements-to-shape, random/reset) | Registered with data present, but the upstream Model/Shape panels were deleted — unreachable orphans. |
| Jaw / face / expression | Deliberately amputated: applying code commented out "per user request" while the backend still computes and writes the data into every pose file. |
| SMPL+H body model | Expected blend (`smplh_model_20260511.blend`) and regressor JSONs absent; no UI can even select it. Registry entry exists, asset never did. |

## Dead or abandoned — do not carry forward

| Item | Note |
|---|---|
| FBX / Alembic / shape export | Fully implemented, never registered (`operators/__init__.py` omits `export.py`). Manifest still claims the permission. |
| .npz animation import (AMASS) | Fully implemented, never registered (`animation.py` not imported). |
| `engine/` (Fast SAM 3D Body) | One successful mesh demo (May), then abandoned. The multiview entry script crashed (`crash_log.txt`: MHR mapping needs a PLY that was never supplied) and is not even present in the copy. MHR-to-SMPL output dir exists and is empty. |
| Rigify blends, `Sam3D_RETARGETING_V2_FAST.blend` (68 MB inside the addon), `PEARTests.blend` | Zero code references; side experiments and leftovers. |
| `patch.py`, `fix_pose.py`, `strip_shapekeys.py` | One-shot migration scripts hardcoded to paths from previous machines. |
| `pytorch3d-main/` vendored source | June 1 compile attempt produced .obj files but no .pyd; runtime used a conda env instead. |
| Image archiving | README claims it; zero implementing code. The clean workspace was manual. |
| "Write pose to console" | Upstream README claim; operator does not exist in the fork. |

## Cross-cutting findings

* The documented `.venv` install path is unproven — every run trace points to Dean's conda env `pear10` (`test_webcam_loop.log`). The install story must be built and tested fresh, not trusted from the POC.
* The POC redistributes licensed MPI assets (SMPL-X blends inside addon `data/`, PEAR asset pack with FLAME/MANO/SMPL-X including a 1.26 GB FLAME texture). Never copy files out of the POC into this repo — reimplement, re-download from official sources locally.
* Hand pose is forced to "flat" ("for SAM3D accuracy"); per-finger pose streaming from PEAR works and is applied. Keep flat default.
* Path archaeology shows a three-machine history; `feature_updates.md` was an agent prompt to port June 1 work onto a stale copy — in this snapshot all four features are already implemented.
* Latent addon-disable bug: operators are unregistered twice (package loop + `serial_ops.unregister()`), raising on disable/reload.
