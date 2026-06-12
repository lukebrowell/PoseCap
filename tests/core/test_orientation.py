import math

import numpy as np
from corridorrig_core import flip_global_orient


def _rotation_matrix(axis_angle: np.ndarray) -> np.ndarray:
    """Independent Rodrigues-formula implementation for cross-checking."""
    angle = float(np.linalg.norm(axis_angle))
    if angle < 1e-12:
        return np.eye(3)
    axis = axis_angle / angle
    k = np.array(
        [
            [0.0, -axis[2], axis[1]],
            [axis[2], 0.0, -axis[0]],
            [-axis[1], axis[0], 0.0],
        ]
    )
    return np.eye(3) + math.sin(angle) * k + (1.0 - math.cos(angle)) * (k @ k)


def test_zero_rotation_is_unchanged() -> None:
    assert np.allclose(flip_global_orient(np.zeros(3)), np.zeros(3))


def test_identity_input_becomes_pure_x_flip() -> None:
    result = flip_global_orient(np.array([1e-13, 0.0, 0.0]))
    assert np.allclose(result, np.zeros(3))


def test_x_180_input_cancels_to_identity() -> None:
    result = flip_global_orient(np.array([math.pi, 0.0, 0.0]))
    assert np.allclose(result, np.zeros(3), atol=1e-9)


def test_matches_independent_matrix_composition() -> None:
    flip = np.array([math.pi, 0.0, 0.0])
    for case in ([0.7, -0.3, 1.1], [0.0, 1.5, 0.0], [-0.2, 0.4, -2.1]):
        case_array = np.array(case)
        expected = _rotation_matrix(flip) @ _rotation_matrix(case_array)
        actual = _rotation_matrix(flip_global_orient(case_array))
        assert np.allclose(actual, expected, atol=1e-9), case
