"""Lightweight ML posture quality label from geometric features (bonus)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Tuple

import numpy as np

try:
    from sklearn.ensemble import RandomForestClassifier
except ImportError:  # pragma: no cover
    RandomForestClassifier = None  # type: ignore[misc, assignment]


Label = Literal["good", "fair", "poor"]


def _rule_label(feats: np.ndarray) -> int:
    """Synthetic oracle: 0=good, 1=fair, 2=poor."""
    elbow_r, elbow_l, knee_r, knee_l, spine_v, sh_tilt, hip_tilt = feats
    asym_knee = abs(knee_r - knee_l)
    asym_elbow = abs(elbow_r - elbow_l)
    score = 0
    if spine_v > 18:
        score += 2
    if sh_tilt > 12 or hip_tilt > 12:
        score += 2
    if asym_knee > 20 or asym_elbow > 25:
        score += 2
    if knee_r < 85 or knee_l < 85:
        score += 1
    if score >= 4:
        return 2
    if score >= 2:
        return 1
    return 0


def _synthetic_dataset(n: int = 800, seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    X = []
    y = []
    for _ in range(n):
        feats = rng.normal(110, 25, size=7).clip(40, 180)
        feats[4] = abs(rng.normal(8, 10))  # spine deviation
        feats[5] = abs(rng.normal(5, 8))
        feats[6] = abs(rng.normal(5, 8))
        lab = _rule_label(feats)
        X.append(feats)
        y.append(lab)
    return np.array(X, dtype=float), np.array(y, dtype=int)


@dataclass
class PostureMLClassifier:
    """
    RandomForest trained on rule-labeled synthetic pose features.
    Serves as a compact learnable surrogate for heuristic screening.
    """

    def __init__(self) -> None:
        self._model = None
        if RandomForestClassifier is not None:
            X, y = _synthetic_dataset()
            self._model = RandomForestClassifier(
                n_estimators=64,
                max_depth=6,
                random_state=0,
            )
            self._model.fit(X, y)

    def predict_label(self, feature_vector: List[float]) -> Label:
        if self._model is None:
            idx = _rule_label(np.array(feature_vector, dtype=float))
        else:
            idx = int(self._model.predict(np.array(feature_vector, dtype=float).reshape(1, -1))[0])
        idx = max(0, min(2, idx))
        return ("good", "fair", "poor")[idx]
