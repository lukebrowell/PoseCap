"""Behavior tests for the character-setup converter presets (task 0008)."""

from posecap_addon.character_setup import (
    SMPLX_BODY_JOINTS,
    UE_MAPPING,
    detect_skeleton_preset,
    mixamo_mapping,
    validate_mapping,
)


def test_ue_mapping_covers_all_smplx_body_joints() -> None:
    assert validate_mapping(UE_MAPPING) == []
    assert set(UE_MAPPING) == set(SMPLX_BODY_JOINTS)


def test_mixamo_mapping_covers_all_smplx_body_joints_with_the_prefix() -> None:
    mapping = mixamo_mapping("mixamorig:")
    assert validate_mapping(mapping) == []
    assert mapping["pelvis"] == "mixamorig:Hips"
    assert mapping["left_hip"] == "mixamorig:LeftUpLeg"
    assert mapping["spine1"] == "mixamorig:Spine"
    assert mapping["spine2"] == "mixamorig:Spine1"
    assert mapping["spine3"] == "mixamorig:Spine2"
    assert mapping["left_collar"] == "mixamorig:LeftShoulder"
    assert mapping["left_shoulder"] == "mixamorig:LeftArm"
    assert mapping["left_elbow"] == "mixamorig:LeftForeArm"
    assert mapping["left_wrist"] == "mixamorig:LeftHand"
    assert mapping["left_foot"] == "mixamorig:LeftToeBase"


def test_detects_the_unreal_skeleton_from_bone_names() -> None:
    bones = {"pelvis", "thigh_l", "thigh_r", "clavicle_l", "spine_05", "hand_r"}
    preset = detect_skeleton_preset(bones)
    assert preset is not None
    assert preset.name == "ue"
    assert preset.mapping == UE_MAPPING


def test_detects_mixamo_with_the_standard_prefix() -> None:
    bones = {"mixamorig:Hips", "mixamorig:LeftUpLeg", "mixamorig:LeftForeArm"}
    preset = detect_skeleton_preset(bones)
    assert preset is not None
    assert preset.name == "mixamo"
    assert preset.mapping["pelvis"] == "mixamorig:Hips"


def test_detects_mixamo_with_a_numbered_prefix() -> None:
    bones = {"mixamorig5:Hips", "mixamorig5:LeftUpLeg", "mixamorig5:LeftForeArm"}
    preset = detect_skeleton_preset(bones)
    assert preset is not None
    assert preset.name == "mixamo"
    assert preset.mapping["pelvis"] == "mixamorig5:Hips"


def test_detects_mixamo_exported_without_a_prefix() -> None:
    bones = {"Hips", "LeftUpLeg", "LeftForeArm", "Spine2", "RightToeBase"}
    preset = detect_skeleton_preset(bones)
    assert preset is not None
    assert preset.name == "mixamo"
    assert preset.mapping["pelvis"] == "Hips"


def test_unknown_skeletons_are_not_detected() -> None:
    assert detect_skeleton_preset({"Bone", "Bone.001", "Bone.002"}) is None


def test_mixamo_characters_skip_the_tpose_re_rest_and_ue_does_not() -> None:
    ue = detect_skeleton_preset({"thigh_l", "clavicle_l", "spine_05"})
    mixamo = detect_skeleton_preset({"mixamorig:Hips", "mixamorig:LeftUpLeg"})
    assert ue is not None and not ue.already_t_pose
    assert mixamo is not None and mixamo.already_t_pose
