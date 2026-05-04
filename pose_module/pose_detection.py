"""MediaPipe Pose wrapper for images and video frames."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import mediapipe as mp
except ImportError as exc:  # pragma: no cover
    raise ImportError("Install mediapipe: pip install mediapipe") from exc


@dataclass
class PoseLandmarkResult:
    """Single-frame pose output."""

    landmarks_norm: List[Tuple[float, float, float]]  # x,y,z in [0,1] image norm
    world_landmarks: Optional[List[Tuple[float, float, float]]] = None
    presence_score: float = 0.0
    frame_index: int = 0
    timestamp_ms: float = 0.0
    extras: Dict[str, Any] = field(default_factory=dict)


class PoseProcessor:
    """
    Runs BlazePose (MediaPipe) on BGR uint8 frames.
    static_image_mode=True for photos; False for video smoothness.
    """

    def __init__(
        self,
        *,
        static_image_mode: bool = False,
        model_complexity: int = 1,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        self._pose = mp.solutions.pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model_complexity,
            smooth_landmarks=True,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def close(self) -> None:
        self._pose.close()

    def __enter__(self) -> "PoseProcessor":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def process_bgr(self, frame_bgr: np.ndarray, frame_index: int = 0) -> Optional[PoseLandmarkResult]:
        if frame_bgr is None or frame_bgr.size == 0:
            return None
        rgb = frame_bgr[:, :, ::-1]
        h, w = rgb.shape[:2]
        res = self._pose.process(rgb)
        if not res.pose_landmarks:
            return None

        lm_list: List[Tuple[float, float, float]] = []
        for lm in res.pose_landmarks.landmark:
            lm_list.append((float(lm.x), float(lm.y), float(lm.z)))

        world = None
        if res.pose_world_landmarks:
            world = [(float(lm.x), float(lm.y), float(lm.z)) for lm in res.pose_world_landmarks.landmark]

        return PoseLandmarkResult(
            landmarks_norm=lm_list,
            world_landmarks=world,
            presence_score=float(res.pose_world_landmarks is not None),
            frame_index=frame_index,
            extras={"image_width": w, "image_height": h},
        )
