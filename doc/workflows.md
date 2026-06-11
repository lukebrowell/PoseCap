# Workflows

Functional flows of the system, diagrammed. This is the "how it works, step by step" companion to [ARCHITECTURE.md](../ARCHITECTURE.md) (which locks the patterns) and the [PRD](product/PRD.md) (which locks the scope). Each section: context first, then the diagram.

All flows describe the target design. Where the POC did something different that we deliberately replaced, a note says so — the evidence behind those calls is in [doc/reference/poc-verification.md](reference/poc-verification.md).

## System context

Three executables, joined by explicit contracts. Blender never imports torch; the engine never imports bpy; the firmware speaks plain CSV. The addon and engine exchange data over two channels only: a localhost TCP stream for live poses, and job files on disk for batch work.

```mermaid
flowchart LR
    CAM(["Webcam"])
    ARD["Arduino firmware<br/>8x AS5600 encoders<br/>via I2C multiplexer"]

    subgraph ENGINE["Engine bridge process - uv venv, CUDA"]
        CAPTURE["Frame capture"]
        INFER["YOLO detect +<br/>PEAR inference"]
        STREAM["TCP pose stream<br/>server"]
        WORKER["Batch job worker"]
    end

    subgraph BLENDER["Blender process - bundled Python"]
        CLIENT["TCP client thread"]
        SERIAL["Serial reader thread"]
        QUEUE["latest-wins queues"]
        TIMER["main-thread timer"]
        APPLY["core: pose mapping,<br/>keyframe policy"]
        UI["panels + operators"]
    end

    JOBS[("job dirs:<br/>images in, poses out")]

    CAM --> CAPTURE --> INFER --> STREAM
    STREAM -- "JSON frames<br/>localhost TCP" --> CLIENT --> QUEUE
    ARD -- "CSV @ 115200 baud<br/>USB serial" --> SERIAL --> QUEUE
    QUEUE --> TIMER --> APPLY --> UI
    UI -- "spawn / stop by PID" --> ENGINE
    UI -- "write job" --> JOBS
    JOBS <--> WORKER
```

## Live webcam streaming and Record Live MoCap

The flagship flow — verified working in the POC (20,329 successful pose loads in the last clean session). Differences from the POC: poses are pushed over TCP instead of polled from a pickle file's mtime; recording is independent of preview (POC trap: recording silently no-oped with preview off); the armature reference is validated every frame (POC's top live failure: 6,670 errors after the armature was deleted mid-stream).

```mermaid
sequenceDiagram
    actor User
    participant UI as Addon UI<br/>(main thread)
    participant BG as TCP client<br/>(background thread)
    participant ENG as Engine bridge
    participant CAM as Webcam

    User->>UI: Start Stream (device N)
    UI->>ENG: spawn process (PID tracked)
    ENG->>ENG: load models (one-time, seconds)
    UI->>BG: start client thread
    BG->>ENG: connect localhost TCP (retry until ready)

    loop every frame (~30 FPS)
        CAM->>ENG: frame
        ENG->>ENG: detect person, infer SMPL-X params
        ENG-->>BG: push JSON pose frame
        BG->>BG: overwrite latest-wins slot
        Note over UI: timer tick (main thread)
        UI->>UI: pop latest, validate armature ref
        UI->>UI: apply pose to bones (quaternions)
        opt recording active
            UI->>UI: insert keyframes at playhead
        end
    end

    User->>UI: Record Live MoCap (toggle, anytime while streaming)
    UI->>UI: start timeline playback, set recording flag

    User->>UI: Stop Stream
    UI->>ENG: terminate by PID handle
    Note over ENG: also self-terminates if<br/>Blender PID disappears
```

## Image-to-pose jobs: single capture and batch

File-based by design — the artifacts on disk are the point (poses you can re-import later). Single capture and batch share one job pipeline; the POC proved both (capture pair + two batch runs on June 8). Progress/failure sidecar text files from the POC are replaced by one status JSON per job.

```mermaid
sequenceDiagram
    actor User
    participant UI as Addon UI
    participant FS as Job dir
    participant ENG as Engine worker

    User->>UI: Capture Pose (timer) / Upload Batch Images
    UI->>FS: create job dir, write job.json<br/>(mode, images or webcam+countdown, params)
    UI->>ENG: spawn worker with job path (PID tracked)

    loop per image / after countdown
        ENG->>ENG: detect + infer
        ENG->>FS: write pose JSON (temp file + atomic rename)
        ENG->>FS: update status.json (progress 0..1)
    end

    alt success
        ENG->>FS: status.json state=done
        UI->>FS: poll status (modal timer)
        UI->>UI: load poses, apply / keyframe
    else failure
        ENG->>FS: status.json state=failed + message
        UI->>User: report error in UI (no raw traceback)
    end
```

## Hardware rig input

The physical encoder rig drives the world transform of a target object; body pose always comes from the engine. Code-complete in the POC, never hardware-proven — first validation happens during the rewrite. The wire format is the POC's proven-simple contract: 8 comma-separated floats per line, no framing.

```mermaid
flowchart TD
    ENC["8x AS5600 encoders<br/>fixed I2C address 0x36"]
    MUX["TCA9548A-class mux @ 0x70<br/>bitmask channel select"]
    FW["Firmware loop @ 50 Hz:<br/>read 12-bit angle, unwrap +/-180,<br/>accumulate cumulative degrees"]
    LINE["CSV line: 8 floats, CRLF<br/>115200 baud"]
    RDR["Serial reader thread:<br/>parse + bounds-check,<br/>drop malformed lines (counted)"]
    SLOT["latest-wins slot<br/>(stale samples dropped)"]
    TMR["bpy timer @ 50 Hz<br/>(main thread)"]
    MAP["per-axis mapping:<br/>channel -> (value - offset) x scale,<br/>optional flip"]
    OBJ["target object<br/>location + rotation_euler"]
    KEY["keyframed only when<br/>capture / recording fires"]

    ENC --> MUX --> FW --> LINE --> RDR --> SLOT --> TMR --> MAP --> OBJ --> KEY
```

Known firmware limits (accepted, documented): unwrap assumes <180 degrees between consecutive reads — very fast spins alias; an unplugged encoder silently repeats its last value. "Reset to Origin" snapshots current channel values as offsets.

## Stream lifecycle

State machine the addon UI reflects. Failure paths are first-class: spawn timeout, socket drop, and engine crash all land back in Stopped with a reported reason — never a stuck UI (POC stopped processes by window title and had no failure states).

```mermaid
stateDiagram-v2
    [*] --> Stopped
    Stopped --> Starting: Start Stream
    Starting --> Streaming: TCP connected,<br/>first frame received
    Starting --> Stopped: spawn/connect timeout<br/>(reported)
    Streaming --> Recording: Record toggle on
    Recording --> Streaming: Record toggle off
    Streaming --> Reconnecting: socket dropped
    Recording --> Reconnecting: socket dropped
    Reconnecting --> Streaming: reconnected
    Reconnecting --> Stopped: engine process dead<br/>(reported)
    Streaming --> Stopped: Stop Stream<br/>(terminate by PID)
    Recording --> Stopped: Stop Stream<br/>(recording finalized first)
```

## Installation

The project tradeoff statement applies here hardest: a working install on the first try beats everything. The POC's documented install path was never actually proven (Dean ran a conda env); this flow ships tested on a clean machine. No source compiles unless no wheel exists — and then gated with explicit progress and actionable failure messages.

```mermaid
flowchart TD
    START(["Run installer"]) --> CHK{"Blender >= 4.2?<br/>NVIDIA driver present?"}
    CHK -- no --> MSG["Actionable message:<br/>what to install, where"] --> FAIL(["Stop"])
    CHK -- yes --> UV["Bootstrap uv,<br/>uv sync (pinned lockfile,<br/>prebuilt wheels)"]
    UV --> WHEEL{"All deps as wheels?"}
    WHEEL -- "no (e.g. PyTorch3D)" --> GATED["Gated source build:<br/>progress shown,<br/>clear failure text"]
    WHEEL -- yes --> EXT
    GATED --> EXT["Install extension zip via<br/>Blender extension system<br/>(no directory junctions)"]
    EXT --> MODELS["Point user at official<br/>SMPL-X download<br/>(licensed, never bundled)"]
    MODELS --> VERIFY["Doctor check:<br/>GPU visible, models found,<br/>engine starts, port free"]
    VERIFY --> DONE(["Ready"])
```

## Reading guide

| Question | Document |
|---|---|
| What is this product, who is it for | [README](../README.md), [PRD](product/PRD.md) |
| How does feature X flow, step by step | this file |
| What patterns bind the code | [ARCHITECTURE.md](../ARCHITECTURE.md) |
| What are the engineering rules | [GUIDELINES.md](../GUIDELINES.md) |
| What did the POC actually prove | [poc-verification.md](reference/poc-verification.md) |
| Why was decision X made | [doc/adr/](adr/) |
