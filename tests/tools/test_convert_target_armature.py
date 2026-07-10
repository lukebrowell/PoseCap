import importlib.util
import math
from pathlib import Path

import pytest


def _load_converter_module():
    module_path = Path(__file__).parents[2] / "tools" / "convert_target_armature.py"
    spec = importlib.util.spec_from_file_location("convert_target_armature", module_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


converter = _load_converter_module()


def test_default_ue_mapping_covers_all_smplx_body_joints() -> None:
    assert converter.validate_mapping(converter.DEFAULT_UE_MAPPING) == []
    assert set(converter.DEFAULT_UE_MAPPING) == set(converter.SMPLX_BODY_JOINTS)


def test_validate_mapping_reports_missing_joints() -> None:
    partial = {name: name for name in converter.SMPLX_BODY_JOINTS if not name.startswith("left_")}
    missing = converter.validate_mapping(partial)
    assert missing and all(name.startswith("left_") for name in missing)


def test_axis_angle_quaternion_matches_quarter_turn() -> None:
    w, x, y, z = converter.axis_angle_quaternion((0.0, 0.0, math.pi / 2))
    assert w == pytest.approx(math.cos(math.pi / 4))
    assert z == pytest.approx(math.sin(math.pi / 4))
    assert x == y == 0.0
    assert converter.axis_angle_quaternion((0.0, 0.0, 0.0)) == (1.0, 0.0, 0.0, 0.0)


def test_probe_expectations_raise_lifts_and_swing_goes_behind() -> None:
    expected = converter.probe_expectations(0.3)
    assert expected["raise_z"] == (-0.3, 0.0, 0.3)
    assert expected["swing_y"] == (-0.3, 0.3, 0.0)


def test_parse_args_defaults_and_overrides() -> None:
    args = converter.parse_args(["--output", "out.blend"])
    assert args.output == "out.blend"
    assert not args.skip_tpose
    assert args.bone_length == 10.0
    assert args.probe_tolerance == 0.05

    args = converter.parse_args(
        ["--output", "o.blend", "--skip-tpose", "--bone-length", "5", "--probe-tolerance", "0.1"]
    )
    assert args.skip_tpose and args.bone_length == 5.0 and args.probe_tolerance == 0.1
