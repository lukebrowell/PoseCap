import math

import numpy as np
from posecap_core import PoseSmoother
from posecap_core.rotation import axis_angle_to_quaternion


def _angle_between(a: np.ndarray, b: np.ndarray) -> float:
    dot = abs(float(np.dot(np.asarray(a), np.asarray(b))))
    return 2.0 * math.acos(min(1.0, dot))


def test_steady_rotation_stream_passes_through_unchanged() -> None:
    smoother = PoseSmoother()
    target = axis_angle_to_quaternion(np.asarray([0.0, 0.0, math.pi / 4]))

    output = None
    for frame in range(60):
        output = smoother.smooth("left_shoulder", target, timestamp=frame / 30.0)

    assert output is not None
    assert _angle_between(output, target) < math.radians(0.5)


def test_jitter_around_still_pose_is_attenuated() -> None:
    rng = np.random.default_rng(7)
    base_vec = np.asarray([0.3, 0.2, 0.1])
    base = axis_angle_to_quaternion(base_vec)
    smoother = PoseSmoother()

    raw_deviation = []
    filtered_deviation = []
    for frame in range(120):
        noisy = axis_angle_to_quaternion(base_vec + rng.normal(0.0, 0.01, 3))
        output = smoother.smooth("pelvis", noisy, timestamp=frame / 30.0)
        if frame >= 30:  # skip filter warm-up
            raw_deviation.append(_angle_between(noisy, base))
            filtered_deviation.append(_angle_between(output, base))

    assert float(np.mean(filtered_deviation)) < 0.6 * float(np.mean(raw_deviation))


def test_fast_motion_follows_without_visible_lag() -> None:
    smoother = PoseSmoother()
    start = axis_angle_to_quaternion(np.asarray([0.0, 0.0, 0.0]))
    target = axis_angle_to_quaternion(np.asarray([0.0, 0.0, math.pi / 2]))

    smoother.smooth("left_shoulder", start, timestamp=0.0)
    output = None
    for frame in range(1, 7):  # 0.2 s at 30 fps
        output = smoother.smooth("left_shoulder", target, timestamp=frame / 30.0)

    assert output is not None
    assert _angle_between(output, target) < math.radians(5.0)


def test_negated_quaternion_is_the_same_rotation_no_pop() -> None:
    smoother = PoseSmoother()
    base = axis_angle_to_quaternion(np.asarray([0.4, 0.1, 0.2]))

    output = None
    for frame in range(30):
        sample = base if frame % 2 == 0 else -base  # alternating hemispheres
        output = smoother.smooth("head", sample, timestamp=frame / 30.0)

    assert output is not None
    assert _angle_between(output, base) < math.radians(1.0)
