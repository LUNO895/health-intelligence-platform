"""Combined coaching suggestions from pose heuristics + nutrition state."""

from __future__ import annotations

from typing import Any, Dict, List

from nutrition_module.bmi_bmr import NutritionMetrics
from nutrition_module.schemas import FitnessGoal, UserHealthProfile


def build_suggestions(
    profile: UserHealthProfile,
    metrics: NutritionMetrics,
    pose_summary: Dict[str, Any],
) -> Dict[str, List[str]]:
    pose_tips: List[str] = []
    for c in pose_summary.get("corrections", [])[:6]:
        pose_tips.append(c)
    if pose_summary.get("mean_pose_score", 100) < 70:
        pose_tips.append("Reduce load or range until form score stabilizes above 70.")
    if pose_summary.get("imbalance_score", 0) > 15:
        pose_tips.append("Add unilateral accessory work to reduce side-to-side asymmetry.")

    diet: List[str] = []
    if profile.fitness_goal == FitnessGoal.fat_loss:
        diet.append("Prioritize protein at each meal to protect lean mass in a deficit.")
    elif profile.fitness_goal == FitnessGoal.muscle_gain:
        diet.append("Add a peri-workout carbohydrate source if sessions exceed 60 minutes.")
    if metrics.bmi_category in ("overweight", "obese"):
        diet.append("Emphasize high-satiety vegetables and lean proteins for adherence.")
    if profile.allergies:
        diet.append(f"Strictly avoid allergens: {', '.join(profile.allergies)}.")

    general = [
        "Hydration: target pale-yellow urine; add electrolytes on long/hot sessions.",
        "Sleep: aim for a consistent 7–9 hour window to support recovery and appetite control.",
        "Recovery: schedule at least one easy or mobility day if training 5+ days per week.",
    ]

    combined: List[str] = []
    combined.extend(pose_tips[:4])
    combined.extend(diet[:3])
    combined.extend(general[:2])

    return {
        "pose": pose_tips,
        "nutrition": diet,
        "general": general,
        "combined": combined,
    }
