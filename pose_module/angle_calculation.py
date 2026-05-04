"""Geometric joint angles and posture alignment from 2D landmarks."""

from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

import numpy as np


def _vec(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return b - a


def angle_degrees(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Angle ABC (vertex at B) in degrees."""
    ba = _vec(b, a)
    bc = _vec(b, c)
    n1 = float(np.linalg.norm(ba))
    n2 = float(np.linalg.norm(bc))
    if n1 < 1e-6 or n2 < 1e-6:
        return float("nan")
    cosang = float(np.clip(np.dot(ba, bc) / (n1 * n2), -1.0, 1.0))
    return math.degrees(math.acos(cosang))


def vertical_deviation_degrees(p_low: np.ndarray, p_high: np.ndarray) -> float:
    """How far the segment from low→high deviates from vertical (0° = perfectly vertical)."""
    v = p_high - p_low
    n = float(np.linalg.norm(v))
    if n < 1e-6:
        return float("nan")
    v = v / n
    vertical = np.array([0.0, -1.0], dtype=float)  # image coords: y grows down
    cosang = float(np.clip(np.dot(v, vertical), -1.0, 1.0))
    return abs(math.degrees(math.acos(cosang)))


def lateral_tilt_degrees(left: np.ndarray, right: np.ndarray) -> float:
    """Absolute roll of shoulder/hip line vs horizontal (symmetry proxy)."""
    d = right - left
    n = float(np.linalg.norm(d))
    if n < 1e-6:
        return float("nan")
    d = d / n
    horiz = np.array([1.0, 0.0], dtype=float)
    cosang = float(np.clip(abs(np.dot(d, horiz)), 0.0, 1.0))
    return math.degrees(math.acos(cosang))


def compute_joint_angles(
    landmarks_norm: Sequence[Tuple[float, float, float]],
) -> Dict[str, float]:
    """
    MediaPipe Pose normalized landmarks (x,y,z visibility) in image space.
    Indices follow https://developers.google.com/mediapipe/solutions/pose
    """
    lm = np.array([[p[0], p[1]] for p in landmarks_norm], dtype=float)

    def p(i: int) -> np.ndarray:
        return lm[i]

    # Right arm: 12 shoulder, 14 elbow, 16 wrist
    elbow_r = angle_degrees(p(14), p(12), p(16))
    # Left arm: 11, 13, 15
    elbow_l = angle_degrees(p(13), p(11), p(15))
    # Right leg: 24 hip, 26 knee, 28 ankle
    knee_r = angle_degrees(p(26), p(24), p(28))
    knee_l = angle_degrees(p(25), p(23), p(27))

    # Trunk: mid-hip to mid-shoulder vs vertical
    mid_sh = (p(11) + p(12)) / 2.0
    mid_hip = (p(23) + p(24)) / 2.0
    spine_vertical_dev = vertical_deviation_degrees(mid_hip, mid_sh)

    shoulder_tilt = lateral_tilt_degrees(p(11), p(12))
    hip_tilt = lateral_tilt_degrees(p(23), p(24))

    return {
        "elbow_right_deg": elbow_r,
        "elbow_left_deg": elbow_l,
        "knee_right_deg": knee_r,
        "knee_left_deg": knee_l,
        "spine_vertical_deviation_deg": spine_vertical_dev,
        "shoulder_tilt_deg": shoulder_tilt,
        "hip_tilt_deg": hip_tilt,
    }


def feature_vector_from_angles(angles: Dict[str, float]) -> List[float]:
    keys = [
        "elbow_right_deg",
        "elbow_left_deg",
        "knee_right_deg",
        "knee_left_deg",
        "spine_vertical_deviation_deg",
        "shoulder_tilt_deg",
        "hip_tilt_deg",
    ]
    out: List[float] = []
    for k in keys:
        v = angles.get(k, float("nan"))
        out.append(0.0 if v != v else float(v))  # NaN → 0
    return out
