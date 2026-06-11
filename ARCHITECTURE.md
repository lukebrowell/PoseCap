# Architecture

System-level patterns and boundaries. Pair with ADRs in `doc/adr/` for individual decisions; step-by-step functional flows are diagrammed in [`doc/workflows.md`](doc/workflows.md).

## Overview

CorridorRig lets an animator drive an SMPL-X body model in Blender from two live inputs: webcam pose estimation (PEAR engine, CUDA) and a physical 8-encoder Arduino rig supplying world position/rotation of a target object. Without it, Corridor's mocap workflow falls back to manual keyframing or external mocap suites. The system is a desktop pipeline on one Windows machine: a Blender extension (runs in Blender's bundled Python), an engine bridge process (uv-managed venv, owns PyTorch/PEAR), and firmware on the Arduino. No server, no database; the boundaries are process and serial-port boundaries.

## Layers & Boundaries

Hexagonal (ports and adapters). Dependency rule: source code dependencies point inward only.

* `contracts/` — wire formats shared by all processes: pose payload schema, serial frame, job status. Pure Python, stdlib only. Imports nothing from any other layer.
* `core/` — domain: pose model (SMPL-X parameter types), retarget/mapping logic, keyframe policy, channel-to-axis mapping. Pure Python plus numpy. Defines ports (abstract interfaces) for pose streams, job queues, rig input, and clock/scheduling. Never imports `bpy`, `torch`, `serial`, sockets, or filesystem APIs.
* `addon/` — Blender adapter: operators, panels, properties, handlers, plus driven adapters (TCP pose-stream client, serial reader, engine process launcher). Only layer that imports `bpy`. UI classes contain no domain logic — they call core through ports.
* `engine/` — PEAR bridge: model loading, inference loop, webcam capture, TCP pose-stream server, batch folder worker. Only layer that imports `torch`/`ultralytics`/PEAR code. Upstream PEAR research code is not in this repo; the bridge imports it from a pinned external location.
* `firmware/` — Arduino sketch. Honors the serial frame defined in `contracts/` (documented there as the canonical spec; firmware cannot import Python).

Crossing rule: addon and engine communicate only through `contracts/` wire formats over the transports below — never by importing each other.

## Patterns

* **IPC — live pose:** localhost TCP, newline-delimited JSON frames, engine is server, addon is client. Push-based; no disk polling, no mtime races. Transport sits behind a core port so it is swappable without touching domain code.
* **IPC — batch/single jobs:** file drop (images in, JSON pose files out) with a per-job JSON status file replacing the POC's `_progress.txt`/`_failed.txt` sidecars. Output written via temp file + `os.replace`.
* **Wire format:** JSON everywhere; pickle is banned for IPC (same deserialization risk class as `weights_only=False`, already banned in AGENTS.md).
* **Blender threading:** no `bpy` calls off the main thread. Background threads (TCP client, serial reader) produce into latest-wins single-slot queues; `bpy.app.timers` callbacks consume on the main thread. This is the only concurrency pattern in the addon.
* **Process lifecycle:** engine spawned and terminated by process handle/PID through a platform adapter — never `shell=True`, never taskkill-by-window-title. Engine self-terminates when the parent Blender PID dies.
* **Error handling:** domain errors defined in `core/`; the addon maps them to `Operator.report` + `{'CANCELLED'}` at the bpy edge; the engine logs them structured and reports failure through the job status file or stream close.
* **Validation:** contracts validate on decode (schema check at the boundary); core receives only typed, validated dataclasses and never re-validates.
* **Licensed assets:** SMPL-X/FLAME/MANO model files and engine weights resolve through configured local paths at runtime; nothing licensed ships in the repo or the extension wheel.

## Naming Conventions

* Packages and modules: `snake_case`. Ports named by role (`PoseStream`, `RigInput`, `JobQueue`); adapters prefixed by technology (`tcp_pose_client`, `serial_rig_input`, `bpy_keyframe_writer`).
* "Rig" means the physical encoder rig. The hardware rig drives object-level location/rotation only; the engine drives body pose. Code and UI keep that vocabulary split.

## Observability

* Logs: stdlib `logging`, one `RotatingFileHandler` per process (addon and engine), bounded size — replaces the POC's unbounded `modal_log.txt`. INFO for lifecycle, DEBUG for per-frame events (off by default).
* Metrics: none — single-user desktop tool. The engine logs inference FPS at INFO on an interval.
* Traces: none.

## Deployment Topology

Desktop, Windows-first. Three artifacts:

* Blender extension zip — built by a repo script that vendors `contracts/` and `core/` into the wheel (uv workspace is the single source of truth); installed through Blender's extension system, not directory junctions.
* Engine bridge — `uv sync` in the repo; launched by the addon or standalone for batch work.
* Firmware — compiled/uploaded via `arduino-cli` or the Arduino IDE.

Platform-specific code (process spawn/kill, COM-port enumeration, webcam enumeration) lives in adapter modules only; core and contracts are platform-neutral.
