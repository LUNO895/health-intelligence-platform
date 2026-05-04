"""Sample a video, run pose + angles, aggregate form and risk heuristics."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from pose_module.angle_calculation import compute_joint_angles, feature_vector_from_angles
from pose_module.pose_detection import PoseProcessor
from pose_module.posture_classifier import PostureMLClassifier


@dataclass
class FrameAnnotation:
    frame_index: int
    angles: Dict[str, float]
    issues: List[str]
    posture_label: str
    score: float


@dataclass
class VideoPoseReport:
    fps: float
    frames_sampled: int
    pose_coverage: float
    mean_pose_score: float
    injury_risk_score: float
    imbalance_score: float
    summary_issues: List[str]
    corrections: List[str]
    frame_samples: List[Dict[str, Any]] = field(default_factory=list)
    worst_frame_index: Optional[int] = None
    preview_frame_path: Optional[str] = None


def _score_frame(angles: Dict[str, float], issues: List[str]) -> float:
    base = 100.0
    base -= 8 * len(issues)
    asym = abs(angles.get("knee_right_deg", 0) - angles.get("knee_left_deg", 0))
    if asym > 15:
        base -= 10
    spine = angles.get("spine_vertical_deviation_deg", 0) or 0
    if spine > 15:
        base -= 12
    return float(max(0.0, min(100.0, base)))


def _issues_from_angles(angles: Dict[str, float]) -> List[str]:
    issues: List[str] = []
    spine = angles.get("spine_vertical_deviation_deg")
    if spine == spine and spine > 18:
        issues.append("Spine alignment deviates from neutral vertical.")

    if angles.get("shoulder_tilt_deg", 0) > 12:
        issues.append("Shoulder line tilt suggests upper-body imbalance.")

    if angles.get("hip_tilt_deg", 0) > 12:
        issues.append("Hip line tilt — check weight distribution.")

    kr, kl = angles.get("knee_right_deg", 0), angles.get("knee_left_deg", 0)
    if abs(kr - kl) > 18:
        issues.append("Knee angle asymmetry — possible lateral imbalance.")

    er, el = angles.get("elbow_right_deg", 0), angles.get("elbow_left_deg", 0)
    if abs(er - el) > 25:
        issues.append("Elbow angle asymmetry — uneven arm loading.")

    return issues


def analyze_video_file(
    video_path: str | Path,
    *,
    stride: int = 3,
    max_frames: int = 300,
    save_preview: bool = True,
    output_dir: Optional[str | Path] = None,
) -> VideoPoseReport:
    """
    stride: process every Nth frame for speed.
    max_frames: safety cap.
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(str(path))

    try:
        import cv2
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Install opencv: pip install opencv-python-headless") from exc

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0) or 30.0

    out_dir = Path(output_dir) if output_dir else path.parent / "_pose_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    clf = PostureMLClassifier()
    processor = PoseProcessor(static_image_mode=False)

    idx = 0
    sampled = 0
    detections = 0
    scores: List[float] = []
    all_issues: List[str] = []
    frame_rows: List[FrameAnnotation] = []
    worst_score = 101.0
    worst_idx: Optional[int] = None
    preview_path: Optional[str] = None

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % stride != 0:
            idx += 1
            continue
        if sampled >= max_frames:
            break

        res = processor.process_bgr(frame, frame_index=idx)
        sampled += 1
        if res:
            detections += 1
            angles = compute_joint_angles(res.landmarks_norm)
            issues = _issues_from_angles(angles)
            fv = feature_vector_from_angles(angles)
            label = clf.predict_label(fv)
            if label == "poor":
                issues.append("ML posture classifier: poor quality window.")
            elif label == "fair" and not issues:
                issues.append("ML posture classifier: fair — refine control.")

            sc = _score_frame(angles, issues)
            scores.append(sc)
            all_issues.extend(issues)
            if sc < worst_score:
                worst_score = sc
                worst_idx = idx
                if save_preview and preview_path is None:
                    preview_file = out_dir / f"pose_preview_{path.stem}.jpg"
                    # draw simple text overlay
                    vis = frame.copy()
                    y0 = 28
                    for line in issues[:3] or ["Pose OK"]:
                        cv2.putText(
                            vis,
                            line[:80],
                            (12, y0),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.55,
                            (0, 0, 255) if issues else (0, 200, 0),
                            2,
                            cv2.LINE_AA,
                        )
                        y0 += 26
                    cv2.imwrite(str(preview_file), vis)
                    preview_path = str(preview_file)

            frame_rows.append(
                FrameAnnotation(
                    frame_index=idx,
                    angles={k: (v if v == v else None) for k, v in angles.items()},
                    issues=issues,
                    posture_label=label,
                    score=sc,
                )
            )
        idx += 1

    cap.release()
    processor.close()

    coverage = float(detections) / float(sampled or 1)
    mean_score = float(np.mean(scores)) if scores else 0.0

    issue_hist: Dict[str, int] = {}
    for iss in all_issues:
        issue_hist[iss] = issue_hist.get(iss, 0) + 1
    summary_issues = [f"{k} (×{v})" for k, v in sorted(issue_hist.items(), key=lambda x: -x[1])[:8]]

    knee_asym = [
        abs((fa.angles.get("knee_right_deg") or 0) - (fa.angles.get("knee_left_deg") or 0))
        for fa in frame_rows
    ]
    imbalance_score = float(np.mean(knee_asym)) if knee_asym else 0.0

    bad_ratio = 1.0 - (mean_score / 100.0)
    injury_risk_score = float(min(100.0, 40 * bad_ratio + 0.5 * imbalance_score))

    corrections = []
    if any("Spine" in s for s in summary_issues):
        corrections.append("Brace core lightly; stack ribs over pelvis; gaze neutral.")
    if any("Shoulder" in s or "Hip" in s for s in summary_issues):
        corrections.append("Film from the back; level shoulders/hips to the camera midline.")
    if any("Knee" in s for s in summary_issues):
        corrections.append("Track knees over toes; avoid valgus collapse on descent.")
    if any("Elbow" in s for s in summary_issues):
        corrections.append("Even elbow bend; keep wrists stacked under shoulders for pushes.")
    if not corrections:
        corrections.append("Maintain controlled tempo; breathe out on exertion.")

    samples_payload: List[Dict[str, Any]] = []
    for fa in frame_rows[:: max(1, len(frame_rows) // 10)][:12]:
        samples_payload.append(
            {
                "frame_index": fa.frame_index,
                "score": round(fa.score, 1),
                "posture_label": fa.posture_label,
                "issues": fa.issues,
                "angles": {k: (round(v, 2) if isinstance(v, float) and v == v else v) for k, v in fa.angles.items()},
            }
        )

    return VideoPoseReport(
        fps=fps,
        frames_sampled=sampled,
        pose_coverage=round(coverage, 3),
        mean_pose_score=round(mean_score, 1),
        injury_risk_score=round(injury_risk_score, 1),
        imbalance_score=round(imbalance_score, 1),
        summary_issues=summary_issues,
        corrections=corrections,
        frame_samples=samples_payload,
        worst_frame_index=worst_idx,
        preview_frame_path=preview_path,
    )


def report_to_dict(rep: VideoPoseReport) -> Dict[str, Any]:
    return {
        "fps": rep.fps,
        "frames_sampled": rep.frames_sampled,
        "pose_coverage": rep.pose_coverage,
        "mean_pose_score": rep.mean_pose_score,
        "injury_risk_score": rep.injury_risk_score,
        "imbalance_score": rep.imbalance_score,
        "summary_issues": rep.summary_issues,
        "corrections": rep.corrections,
        "frame_samples": rep.frame_samples,
        "worst_frame_index": rep.worst_frame_index,
        "preview_frame_path": rep.preview_frame_path,
    }
