"""One Euro smoothing for streamed pose quaternions (Casiez et al., CHI 2012).

Grounded 2026-07-10: quaternion adaptation follows VRPN's vrpn_OneEuroFilter.h
(angular derivative from the relative rotation, low-pass via slerp); MediaPipe's
pose pipeline applies the same filter family as its final stage. Deviation from
VRPN: the derivative is tracked as a scalar angular speed, not a derivative
quaternion. Under axis-flipping jitter the scalar cannot cancel directionally,
so it reads a HIGHER speed than VRPN's vector low-pass would — the cutoff rises
and the filter smooths less. The approximation is therefore conservative: it can
under-smooth pathological jitter, never add lag beyond the reference. Pure
module — no Blender imports — mirroring the LimbFilter pattern.
"""

import math
from dataclasses import dataclass

import numpy as np

from .errors import PoseCapError
from .rotation import FloatArray

_FALLBACK_INTERVAL_SECONDS = 1.0 / 30.0


@dataclass
class _BoneState:
    filtered: np.ndarray
    speed: float
    timestamp: float


class PoseSmoother:
    """Per-bone One Euro filter over a stream of rotation quaternions.

    min_cutoff (Hz) sets jitter suppression at rest; beta scales the cutoff
    with angular speed (rad/s) so fast motion follows without lag. Defaults are
    the Casiez starting point (min_cutoff 1 Hz), validated visually on the
    dance-fixture live demo (2026-07-10) — no visible lag on fast moves.
    """

    def __init__(
        self,
        *,
        min_cutoff: float = 1.0,
        beta: float = 0.5,
        derivative_cutoff: float = 1.0,
    ) -> None:
        if min_cutoff <= 0 or derivative_cutoff <= 0:
            raise PoseCapError("cutoff frequencies must be positive")
        if beta < 0:
            raise PoseCapError("beta must not be negative")
        self._min_cutoff = min_cutoff
        self._beta = beta
        self._derivative_cutoff = derivative_cutoff
        self._states: dict[str, _BoneState] = {}

    def smooth(self, bone_name: str, quaternion: FloatArray, timestamp: float) -> FloatArray:
        """Return the filtered quaternion for this bone at this timestamp.

        timestamp is the frame's capture time in SECONDS (any monotonic epoch);
        frame-to-frame deltas drive the filter, so mixing epochs between calls
        for the same bone breaks the adaptive cutoff. Non-increasing timestamps
        fall back to a 1/30 s interval.
        """
        sample = np.asarray(quaternion, dtype=np.float64)
        state = self._states.get(bone_name)
        if state is None:
            self._states[bone_name] = _BoneState(sample.copy(), 0.0, timestamp)
            return sample

        interval = timestamp - state.timestamp
        if interval <= 0.0:
            interval = _FALLBACK_INTERVAL_SECONDS
        if float(np.dot(sample, state.filtered)) < 0.0:
            sample = -sample

        speed = _angle_between(sample, state.filtered) / interval
        speed_alpha = _smoothing_factor(interval, self._derivative_cutoff)
        speed_hat = speed_alpha * speed + (1.0 - speed_alpha) * state.speed

        cutoff = self._min_cutoff + self._beta * speed_hat
        alpha = _smoothing_factor(interval, cutoff)
        filtered = _slerp(state.filtered, sample, alpha)

        self._states[bone_name] = _BoneState(filtered, speed_hat, timestamp)
        result = filtered.copy()
        result.setflags(write=False)
        return result


def _smoothing_factor(interval: float, cutoff: float) -> float:
    tau = 1.0 / (2.0 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / interval)


def _angle_between(a: np.ndarray, b: np.ndarray) -> float:
    dot = min(1.0, abs(float(np.dot(a, b))))
    return 2.0 * math.acos(dot)


def _slerp(start: np.ndarray, end: np.ndarray, fraction: float) -> np.ndarray:
    dot = float(np.dot(start, end))
    if dot < 0.0:
        end = -end
        dot = -dot
    if dot > 0.9995:  # nearly parallel: nlerp avoids the degenerate sin term
        blended = start + fraction * (end - start)
        return blended / np.linalg.norm(blended)
    theta = math.acos(min(1.0, dot))
    sin_theta = math.sin(theta)
    weight_start = math.sin((1.0 - fraction) * theta) / sin_theta
    weight_end = math.sin(fraction * theta) / sin_theta
    return weight_start * start + weight_end * end
