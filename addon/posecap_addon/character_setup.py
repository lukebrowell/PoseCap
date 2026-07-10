"""Convert a humanoid character armature to the PoseCap target convention.

Implements doc/workflows.md § "Target armature requirements" for armatures
that don't follow it: (1) optionally re-rest the arms to a T-pose, (2)
rename mapped bones to SMPL-X joint names (vertex groups follow), (3)
reorient mapped bones (+Z tails, local z toward -Y) so pose-bone local axes
equal the SMPL-X joint frame, then (4) self-verify with synthetic
left_shoulder raise/swing probes.

Presets ship for the Unreal Engine humanoid skeleton (validated on two
Fortnite exports) and the Mixamo skeleton (Adobe's free character library;
grounded on the mixamorig <-> SMPL correspondence used across retarget
tools). Skeleton family is auto-detected from bone names.

This module is loadable standalone (stdlib only; ``bpy`` arrives as a
parameter) so the dev CLI in tools/convert_target_armature.py can run it
inside ``blender --background`` without the extension installed. It shares
no imports with the rest of the addon on purpose.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

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
UE_MAPPING: dict[str, str] = {
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

# Mixamo skeleton suffixes (index-aligned with the SMPL joint order; the
# export prefix varies — "mixamorig:", "mixamorig5:", or none at all).
_MIXAMO_SUFFIXES: dict[str, str] = {
    "pelvis": "Hips",
    "left_hip": "LeftUpLeg",
    "right_hip": "RightUpLeg",
    "spine1": "Spine",
    "left_knee": "LeftLeg",
    "right_knee": "RightLeg",
    "spine2": "Spine1",
    "left_ankle": "LeftFoot",
    "right_ankle": "RightFoot",
    "spine3": "Spine2",
    "left_foot": "LeftToeBase",
    "right_foot": "RightToeBase",
    "neck": "Neck",
    "left_collar": "LeftShoulder",
    "right_collar": "RightShoulder",
    "head": "Head",
    "left_shoulder": "LeftArm",
    "right_shoulder": "RightArm",
    "left_elbow": "LeftForeArm",
    "right_elbow": "RightForeArm",
    "left_wrist": "LeftHand",
    "right_wrist": "RightHand",
}

_MIXAMO_PREFIX_PATTERN = re.compile(r"^(mixamorig\d*[:_])Hips$")

# Arm chains re-rested to a T-pose: (bone, reference child whose HEAD gives
# the limb direction — UE exports orient bone tails off-limb, so tails lie).
_UE_ARM_CHAINS = {
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
ArmChains = dict[str, tuple[tuple[str, str], ...]]


class ConversionError(RuntimeError):
    """A conversion failure with a user-facing message."""


@dataclass(frozen=True)
class SkeletonPreset:
    """One convertible skeleton family."""

    name: str
    label: str
    mapping: dict[str, str]
    arm_chains: ArmChains
    already_t_pose: bool


@dataclass(frozen=True)
class ConversionResult:
    """Self-verification outcome of a conversion."""

    probe_lines: tuple[str, ...]
    max_probe_error: float


def ue_preset() -> SkeletonPreset:
    return SkeletonPreset(
        name="ue",
        label="Unreal Engine / Fortnite",
        mapping=dict(UE_MAPPING),
        arm_chains=_UE_ARM_CHAINS,
        already_t_pose=False,
    )


def mixamo_mapping(prefix: str) -> dict[str, str]:
    """The Mixamo bone mapping for one export prefix ('' when stripped)."""
    return {joint: prefix + suffix for joint, suffix in _MIXAMO_SUFFIXES.items()}


def mixamo_preset(prefix: str) -> SkeletonPreset:
    # Mixamo characters download in T-pose; the UE-style A-pose re-rest
    # would corrupt an already correct rest pose.
    chains: ArmChains = {
        "l": (
            (prefix + "LeftArm", prefix + "LeftForeArm"),
            (prefix + "LeftForeArm", prefix + "LeftHand"),
            (prefix + "LeftHand", prefix + "LeftHandMiddle1"),
        ),
        "r": (
            (prefix + "RightArm", prefix + "RightForeArm"),
            (prefix + "RightForeArm", prefix + "RightHand"),
            (prefix + "RightHand", prefix + "RightHandMiddle1"),
        ),
    }
    return SkeletonPreset(
        name="mixamo",
        label="Mixamo",
        mapping=mixamo_mapping(prefix),
        arm_chains=chains,
        already_t_pose=True,
    )


def detect_skeleton_preset(bone_names: set[str] | frozenset[str]) -> SkeletonPreset | None:
    """Sniff the skeleton family from bone names (None when unrecognized)."""
    names = set(bone_names)
    if {"thigh_l", "clavicle_l"} <= names:
        return ue_preset()
    for name in names:
        match = _MIXAMO_PREFIX_PATTERN.match(name)
        if match and match.group(1) + "LeftUpLeg" in names:
            return mixamo_preset(match.group(1))
    if {"Hips", "LeftUpLeg", "LeftForeArm"} <= names:
        return mixamo_preset("")
    return None


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
    """Expected world elbow displacement per probe on a correct armature.

    raise_z (+z 90 deg): the T-pose arm (along +X) swings up — the elbow rises
    by the shoulder-to-elbow length and pulls inward by the same amount.
    swing_y (+y 90 deg): the arm swings behind the body (+Y world).
    """
    return {
        "raise_z": (-arm_length, 0.0, arm_length),
        "swing_y": (-arm_length, arm_length, 0.0),
    }


def convert_armature(
    bpy,
    arm_obj,
    preset: SkeletonPreset,
    *,
    re_rest_t_pose: bool | None = None,
    bone_length: float = 10.0,
    probe_tolerance: float = 0.05,
) -> ConversionResult:  # pragma: no cover - exercised inside Blender only
    """Convert one armature in the open file; raises ConversionError on failure."""
    missing_joints = validate_mapping(preset.mapping)
    if missing_joints:
        raise ConversionError(f"mapping is missing SMPL-X joints: {', '.join(missing_joints)}")
    mesh_objs = _resolve_meshes(bpy, arm_obj, preset.mapping)
    needs_re_rest = not preset.already_t_pose if re_rest_t_pose is None else re_rest_t_pose
    if needs_re_rest:
        _re_rest_tpose(bpy, arm_obj, mesh_objs, preset.arm_chains)
    _rename_and_reorient(bpy, arm_obj, mesh_objs, preset.mapping, bone_length)
    return _verify(bpy, arm_obj, probe_tolerance)


def _resolve_meshes(bpy, arm_obj, mapping):  # pragma: no cover - Blender only
    if arm_obj is None or getattr(arm_obj, "type", None) != "ARMATURE":
        raise ConversionError("pick an armature object first")
    mesh_objs = [
        o
        for o in bpy.data.objects
        if o.type == "MESH"
        and any(m.type == "ARMATURE" and m.object is arm_obj for m in o.modifiers)
    ]
    if not mesh_objs:
        raise ConversionError("no mesh is bound to this armature")
    absent = [bone for bone in mapping.values() if bone not in arm_obj.pose.bones]
    if absent:
        raise ConversionError(f"the armature is missing expected bones: {', '.join(absent)}")
    return mesh_objs


def _re_rest_tpose(bpy, arm_obj, mesh_objs, arm_chains):  # pragma: no cover - Blender only
    from mathutils import Matrix, Vector  # type: ignore  # Blender-bundled module

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
        for bone, child in arm_chains[side]:
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
    from mathutils import Vector  # type: ignore  # Blender-bundled module

    for smpl_name, source_name in mapping.items():
        arm_obj.data.bones[source_name].name = smpl_name
    for mesh_obj in mesh_objs:
        for smpl_name, source_name in mapping.items():
            group = mesh_obj.vertex_groups.get(source_name)
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
    lines: list[str] = []
    max_error = 0.0
    for label, axis_angle in probes:
        delta = apply_shoulder(axis_angle)
        want = expected[label]
        error = max(abs(delta[i] - want[i]) for i in range(3))
        max_error = max(max_error, error)
        lines.append(
            f"probe {label}: delta=({delta.x:+.3f},{delta.y:+.3f},{delta.z:+.3f}) "
            f"expected=({want[0]:+.3f},{want[1]:+.3f},{want[2]:+.3f}) err={error:.4f}"
        )
        if error > tolerance:
            raise ConversionError(
                f"probe {label} failed: error {error:.4f} > tolerance {tolerance:.4f}"
            )
    for pose_bone in arm_obj.pose.bones:
        pose_bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    return ConversionResult(probe_lines=tuple(lines), max_probe_error=max_error)
