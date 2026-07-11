# Task `0011`: Extract the armature retarget engine into `core/`

**Status:** done
**Created:** 2026-07-10
**Owner:** alexandremendoncaalvaro
**Execution:** AFK
**Spec ref:**
**Board ref:**

## Context

ARCHITECTURE.md's layer definition assigns retarget/mapping logic to `core/`
("core/ — domain: pose model (SMPL-X parameter types), retarget/mapping
logic, keyframe policy"). The v0.1.3 slice landed the character converter as
`addon/posecap_addon/character_setup.py`, which places the pure retarget
domain (SMPL-X joint tables, `axis_angle_quaternion`, `probe_expectations`,
`SkeletonPreset`, `detect_skeleton_preset`, `validate_mapping`) in the wrong
layer. A fresh-context `/ad-review` (Standards axis, 2026-07-10) flagged this
as a Concern and noted the concrete duplication: `character_setup.py`'s
`axis_angle_quaternion` reimplements `posecap_core.rotation.axis_angle_to_quaternion`
(its own docstring says "mirrors core.rotation semantics").

The deviation was deliberate under a real constraint, not an oversight: the
module is stdlib-only and file-path-loadable so `tools/convert_target_armature.py`
can run it inside `blender --background` from a repo checkout where
`posecap_core` is not installed on Blender's bundled Python. Any extraction
must preserve that dev/CI path (or replace it). This task pays down the
architectural debt without regressing the converter.

## Acceptance Criteria

- [x] Pure retarget logic (joint order, mapping tables, preset detection,
      mapping validation, probe math) lives in `core/` and is imported by the
      addon, not duplicated.
- [x] `axis_angle_quaternion` is gone from the addon path; the single
      implementation is `posecap_core.rotation.axis_angle_to_quaternion`
      (or a thin core wrapper), with numeric parity proven by a test.
- [x] `import-linter` still passes: `core/` imports stdlib + numpy +
      `contracts/` only; no `bpy`/`mathutils` leak into `core/`.
- [x] `tools/convert_target_armature.py` still converts an armature inside
      `blender --background` (or is replaced by a documented equivalent that
      needs no terminal for the end user — PRD constraint unchanged).
- [x] All existing converter tests (`tests/addon/test_character_setup.py`,
      `tests/addon/test_character_setup_panel.py`,
      `tests/tools/test_convert_target_armature.py`) pass unchanged in intent,
      relocated to `tests/core/` where they now test core.
- [x] Full local gate matrix green (ruff, format, pyright Windows + Linux,
      import-linter, pytest).

## Plan

- [x] Ground: confirm whether the addon may import `posecap_core` at runtime
      (it is vendored into the extension wheel — verify) and how the dev CLI
      resolves imports inside `blender --background`.
- [x] Move the pure functions/tables into a new `core/src/posecap_core/`
      module (e.g. `retarget.py`); re-export the needed names.
- [x] Replace the addon `axis_angle_quaternion` with the core function;
      keep the `bpy`-orchestration functions (`_re_rest_tpose`,
      `_rename_and_reorient`, `_verify`, `convert_armature`) in the addon.
- [x] Resolve the dev-CLI import path: either make the shim add the workspace
      `core/src` to `sys.path` before load, or vendor the needed core module
      alongside it — whichever keeps `blender --background` working.
- [x] Relocate the pure tests to `tests/core/`; keep the operator/UI tests in
      `tests/addon/`.
- [x] Run the full gate matrix; `/ad-review` the diff before merge.

## Notes

Append-only log. Date each entry. Never rewrite past entries.

### 2026-07-10

Created from the v0.1.3 `/ad-review` Standards-axis Concern. Not a release
blocker — the duplication is numerically correct and the deviation is
justified by the stdlib-only dev-CLI constraint; this task removes the debt
deliberately rather than under release pressure.

### 2026-07-11

Done. Pure retarget domain moved verbatim to `core/src/posecap_core/retarget.py`
(tables, `SkeletonPreset`, presets, `detect_skeleton_preset`, `validate_mapping`,
`probe_expectations`) and re-exported at `posecap_core` top level to match the
package's flat re-export idiom. `addon/posecap_addon/character_setup.py` is now a
facade over that domain plus the `bpy` orchestration; its stdlib
`axis_angle_quaternion` is deleted — `_verify` uses
`posecap_core.rotation.axis_angle_to_quaternion`, with parity pinned by
`tests/core/test_retarget.py::test_core_quaternion_has_parity_with_the_removed_addon_helper`.

Dev-CLI path resolved via the shim (option 1): `_ensure_workspace_packages_importable`
front-inserts workspace `core/src` + `contracts/src` on `sys.path` before loading
`character_setup` by file path. Insertion is UNCONDITIONAL and load-bearing —
Blender exposes an installed extension's *vendored* (possibly stale) `posecap_core`
on `sys.path` even under `--factory-startup`, so the workspace roots must shadow it.
A `find_spec`-guarded version was tried and reverted after a `blender
--background --factory-startup` run imported the stale vendored copy and failed on
the new `ARM_TARGETS` export (caught by verification, not by the unit gate).

Verified: full local gate green (ruff, format, pyright Win+Linux, import-linter,
pytest 260 passed); dev CLI loads in `blender --background --factory-startup` with
`posecap_core` resolving from `core/src` and all pure funcs + the core quaternion
correct. Two-axis `/ad-review` clean (Spec: all ACs met, no creep; Standards: no
blockers). The four Standards Concerns were fixed in-slice: dead `Quaternion` alias
removed, `ConversionError` rooted in `PoseCapError` (§2.2), `retarget` re-exported at
`posecap_core` top level, and the sys.path guard reverted (above). The full
end-to-end conversion of a real UE/Mixamo armature was not re-run (no licensed asset
in the repo); the conversion `bpy` code is unchanged and was validated on two
Fortnite armatures on 2026-07-10.

## Definition of Done

All Acceptance Criteria checked, plus:

- [x] Local tests pass (or N/A documented in Notes)
- [x] Code review completed (human or fresh-context reviewer per WORKFLOW §10)
- [x] No orphan `TODO`/`FIXME` introduced
- [x] Status updated to `done` and Notes log closes the task
