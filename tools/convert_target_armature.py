"""Convert a humanoid rig into the PoseCap target-armature convention.

Implements doc/workflows.md § "Target armature requirements" for rigs that
don't follow it (UE/Fortnite exports, Mixamo, …): (1) optionally re-rest the
arms to a T-pose (bake mesh, pose-as-rest), (2) rename mapped bones to SMPL-X
joint names (vertex groups follow), (3) reorient mapped bones (+Z tails,
local z toward -Y) so pose-bone local axes equal the SMPL-X joint frame in
Blender's z-up world, then (4) self-verify with synthetic left_shoulder
raise/swing probes before saving.

Run inside Blender:

    blender --background rig.blend --python tools/convert_target_armature.py \
        -- --output converted.blend [--mapping mapping.json] [--skip-tpose]
        [--bone-length 10.0] [--probe-tolerance 0.05]

The default mapping targets the Unreal Engine humanoid skeleton. A custom
mapping JSON maps SMPL-X joint names to rig bone names. Validated 2026-07-10
on two Fortnite rigs (M_MED_Rebirth_Soldier, M_MED_Donut).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

SMPLX_BODY_JOINTS = (
    "pelvis",
    "left_hip",
    "right_hip",
    "spine1",
    "left_knee",
    "right_knee",
    "spine2",
    "left_ankle",
    "right_ankle",
    "spine3",
    "left_foot",
    "right_foot",
    "neck",
    "left_collar",
    "right_collar",
    "head",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
)

# Unreal Engine humanoid skeleton (Fortnite exports use it verbatim).
DEFAULT_UE_MAPPING: dict[str, str] = {
    "pelvis": "pelvis",
    "left_hip": "thigh_l",
    "right_hip": "thigh_r",
    "spine1": "spine_01",
    "left_knee": "calf_l",
    "right_knee": "calf_r",
    "spine2": "spine_03",
    "left_ankle": "foot_l",
    "right_ankle": "foot_r",
    "spine3": "spine_05",
    "left_foot": "ball_l",
    "right_foot": "ball_r",
    "neck": "neck_01",
    "left_collar": "clavicle_l",
    "right_collar": "clavicle_r",
    "head": "head",
    "left_shoulder": "upperarm_l",
    "right_shoulder": "upperarm_r",
    "left_elbow": "lowerarm_l",
    "right_elbow": "lowerarm_r",
    "left_wrist": "hand_l",
    "right_wrist": "hand_r",
}

# Arm chains re-rested to a T-pose: (bone, reference child whose HEAD gives
# the limb direction — UE exports orient bone tails off-limb, so tails lie).
ARM_CHAINS = {
    "l": (
        ("upperarm_l", "lowerarm_l"),
        ("lowerarm_l", "hand_l"),
        ("hand_l", "middle_metacarpal_l"),
    ),
    "r": (
        ("upperarm_r", "lowerarm_r"),
        ("lowerarm_r", "hand_r"),
        ("hand_r", "middle_metacarpal_r"),
    ),
}
ARM_TARGETS = {"l": (1.0, 0.0, 0.0), "r": (-1.0, 0.0, 0.0)}

Quaternion = tuple[float, float, float, float]


def validate_mapping(mapping: dict[str, str]) -> list[str]:
    """Return the SMPL-X joints missing from a mapping (empty = valid)."""
    return [name for name in SMPLX_BODY_JOINTS if name not in mapping]


def axis_angle_quaternion(axis_angle: tuple[float, float, float]) -> Quaternion:
    """WXYZ quaternion from a Rodrigues vector — mirrors core.rotation semantics."""
    x, y, z = axis_angle
    angle = math.sqrt(x * x + y * y + z * z)
    if angle < 1e-12:
        return (1.0, 0.0, 0.0, 0.0)
    half = angle / 2.0
    scale = math.sin(half) / angle
    return (math.cos(half), x * scale, y * scale, z * scale)


def probe_expectations(arm_length: float) -> dict[str, tuple[float, float, float]]:
    """Expected world elbow displacement per probe on a correct rig.

    raise_z (+z 90 deg): the T-pose arm (along +X) swings up — the elbow rises
    by the shoulder-to-elbow length and pulls inward by the same amount.
    swing_y (+y 90 deg): the arm swings behind the body (+Y world).
    """
    return {
        "raise_z": (-arm_length, 0.0, arm_length),
        "swing_y": (-arm_length, arm_length, 0.0),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a rig to the PoseCap armature convention."
    )
    parser.add_argument("--output", required=True, help="Path for the converted .blend")
    parser.add_argument("--mapping", help="JSON file mapping SMPL-X joint names to rig bone names")
    parser.add_argument(
        "--skip-tpose",
        action="store_true",
        help="Skip the A-pose to T-pose re-rest (rig is already T-pose)",
    )
    parser.add_argument(
        "--bone-length",
        type=float,
        default=10.0,
        help="Reoriented bone length in armature units (visual only)",
    )
    parser.add_argument(
        "--probe-tolerance",
        type=float,
        default=0.05,
        help="Relative tolerance for the self-verification probes",
    )
    return parser.parse_args(argv)


def _script_args() -> list[str]:
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1 :]
    return []


def _load_mapping(args: argparse.Namespace) -> dict[str, str]:
    mapping = dict(DEFAULT_UE_MAPPING)
    if args.mapping:
        mapping.update(json.loads(Path(args.mapping).read_text(encoding="utf-8")))
    missing = validate_mapping(mapping)
    if missing:
        sys.exit(f"mapping is missing SMPL-X joints: {', '.join(missing)}")
    return mapping


def _resolve_scene(bpy, mapping):  # pragma: no cover - Blender only
    arm_obj = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    if arm_obj is None:
        sys.exit("no armature object in this .blend")
    mesh_objs = [
        o
        for o in bpy.data.objects
        if o.type == "MESH"
        and any(m.type == "ARMATURE" and m.object is arm_obj for m in o.modifiers)
    ]
    if not mesh_objs:
        sys.exit("no mesh bound to the armature")
    absent = [rig for rig in mapping.values() if rig not in arm_obj.pose.bones]
    if absent:
        sys.exit(f"rig is missing mapped bones: {', '.join(absent)}")
    return arm_obj, mesh_objs


def _re_rest_tpose(bpy, arm_obj, mesh_objs):  # pragma: no cover - Blender only
    from mathutils import Matrix, Vector

    def align(name, reference_child, target):
        bpy.context.view_layer.update()
        pose_bone = arm_obj.pose.bones[name]
        world = arm_obj.matrix_world
        head_world = world @ pose_bone.head
        tip = (
            world @ arm_obj.pose.bones[reference_child].head
            if reference_child
            else world @ pose_bone.tail
        )
        direction = (tip - head_world).normalized()
        rotation = direction.rotation_difference(Vector(target)).to_matrix().to_4x4()
        pivot = Matrix.Translation(head_world)
        pose_bone.matrix = world.inverted() @ (
            pivot @ rotation @ pivot.inverted() @ (world @ pose_bone.matrix)
        )

    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    for side, target in ARM_TARGETS.items():
        for bone, child in ARM_CHAINS[side]:
            if bone in arm_obj.pose.bones:
                align(bone, child if child in arm_obj.pose.bones else None, target)
    bpy.ops.object.mode_set(mode="OBJECT")
    for mesh_obj in mesh_objs:
        bpy.context.view_layer.objects.active = mesh_obj
        modifier = next(m for m in mesh_obj.modifiers if m.type == "ARMATURE")
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        rebind = mesh_obj.modifiers.new("Armature", "ARMATURE")
        rebind.object = arm_obj
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def _rename_and_reorient(bpy, arm_obj, mesh_objs, mapping, bone_length):
    # pragma: no cover - Blender only
    from mathutils import Vector

    for smpl_name, rig_name in mapping.items():
        arm_obj.data.bones[rig_name].name = smpl_name
    for mesh_obj in mesh_objs:
        for smpl_name, rig_name in mapping.items():
            group = mesh_obj.vertex_groups.get(rig_name)
            if group is not None:
                group.name = smpl_name

    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    for smpl_name in mapping:
        edit_bone = arm_obj.data.edit_bones[smpl_name]
        head = edit_bone.head.copy()
        edit_bone.tail = head + Vector((0.0, 0.0, bone_length))
        edit_bone.align_roll(Vector((0.0, -1.0, 0.0)))
    bpy.ops.object.mode_set(mode="OBJECT")


def _verify(bpy, arm_obj, relative_tolerance):  # pragma: no cover - Blender only
    def elbow_world():
        bpy.context.view_layer.update()
        return (arm_obj.matrix_world @ arm_obj.pose.bones["left_elbow"].head).copy()

    def apply_shoulder(axis_angle):
        for pose_bone in arm_obj.pose.bones:
            pose_bone.rotation_mode = "QUATERNION"
            pose_bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        before = elbow_world()
        quaternion = axis_angle_quaternion(axis_angle)
        arm_obj.pose.bones["left_shoulder"].rotation_quaternion = quaternion
        return elbow_world() - before

    scale = arm_obj.matrix_world.to_scale()[0]
    shoulder = arm_obj.pose.bones["left_shoulder"].head
    elbow = arm_obj.pose.bones["left_elbow"].head
    arm_length = (elbow - shoulder).length * scale
    tolerance = max(relative_tolerance * arm_length, 1e-4)
    expected = probe_expectations(arm_length)
    probes = (("raise_z", (0.0, 0.0, math.pi / 2)), ("swing_y", (0.0, math.pi / 2, 0.0)))
    for label, axis_angle in probes:
        delta = apply_shoulder(axis_angle)
        want = expected[label]
        error = max(abs(delta[i] - want[i]) for i in range(3))
        print(
            f"probe {label}: delta=({delta.x:+.3f},{delta.y:+.3f},{delta.z:+.3f}) "
            f"expected=({want[0]:+.3f},{want[1]:+.3f},{want[2]:+.3f}) err={error:.4f}"
        )
        if error > tolerance:
            sys.exit(f"probe {label} failed: error {error:.4f} > tolerance {tolerance:.4f}")
    for pose_bone in arm_obj.pose.bones:
        pose_bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)


def main() -> None:  # pragma: no cover - exercised inside Blender only
    import bpy

    args = parse_args(_script_args())
    mapping = _load_mapping(args)
    arm_obj, mesh_objs = _resolve_scene(bpy, mapping)
    if not args.skip_tpose:
        _re_rest_tpose(bpy, arm_obj, mesh_objs)
    _rename_and_reorient(bpy, arm_obj, mesh_objs, mapping, args.bone_length)
    _verify(bpy, arm_obj, args.probe_tolerance)

    # keep external texture references valid at the new save location
    bpy.ops.file.make_paths_absolute()
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.output).resolve()))
    print(f"converted rig saved: {args.output}")


if __name__ == "__main__":
    main()
