"""Merge Module 1 + Module 2 into a structured combined report."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import gemini_integration
from nutrition_module.bmi_bmr import NutritionMetrics, compute_nutrition_metrics, metrics_to_dict
from nutrition_module.meal_planner import WeeklyMealPlan, build_weekly_plan
from nutrition_module.schemas import UserHealthProfile
from suggestion_engine.engine import build_suggestions
from pose_module.video_analyzer import VideoPoseReport, report_to_dict


@dataclass
class CombinedHealthReport:
    user_profile: Dict[str, Any]
    pose_analysis: Dict[str, Any]
    nutrition_analysis: Dict[str, Any]
    meal_plan: Dict[str, Any]
    health_risk_indicators: Dict[str, Any]
    recommendations: Dict[str, Any]
    gemini: Optional[Dict[str, Any]] = None
    human_readable: str = ""

    def to_json(self) -> str:
        payload = {
            "user_profile": self.user_profile,
            "pose_analysis": self.pose_analysis,
            "nutrition_analysis": self.nutrition_analysis,
            "meal_plan": self.meal_plan,
            "health_risk_indicators": self.health_risk_indicators,
            "recommendations": self.recommendations,
            "gemini": self.gemini,
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def to_dict(self) -> Dict[str, Any]:
        return json.loads(self.to_json())


def _risks(pose: Dict[str, Any], metrics: NutritionMetrics) -> Dict[str, Any]:
    return {
        "pose_injury_risk_score": pose.get("injury_risk_score"),
        "pose_imbalance_score": pose.get("imbalance_score"),
        "bmi_category": metrics.bmi_category,
        "bmi": metrics.bmi,
        "notes": [
            "Scores are heuristic screening aids, not clinical instruments.",
            "Seek professional evaluation for pain, dizziness, or acute injury.",
        ],
    }


def build_combined_report(
    profile: UserHealthProfile,
    pose_report: VideoPoseReport | Dict[str, Any] | None,
    *,
    use_gemini: bool = True,
) -> CombinedHealthReport:
    metrics = compute_nutrition_metrics(profile)
    plan = build_weekly_plan(profile, metrics)

    pose_dict = report_to_dict(pose_report) if isinstance(pose_report, VideoPoseReport) else (pose_report or {})
    nutrition_dict = {
        "anthropometrics": metrics_to_dict(metrics),
        "allergies": profile.allergies,
        "diet_preference": profile.diet_preference.value,
        "goal": profile.fitness_goal.value,
    }

    suggestions = build_suggestions(profile, metrics, pose_dict)

    gemini_payload = None
    if use_gemini:
        fallback = {
            "executive_summary": "Gemini not configured — using rule-based summaries only.",
            "pose_highlights": [],
            "nutrition_highlights": [],
            "risk_warnings": [],
            "personalized_suggestions": suggestions.get("combined", [])[:8],
            "sleep_hydration_recovery": suggestions.get("general", []),
        }
        gemini_payload = gemini_integration.safe_gemini_call(
            lambda: gemini_integration.combined_health_insights_blob(
                profile.model_dump(),
                pose_dict,
                nutrition_dict,
            ),
            fallback,
        )

    risks = _risks(pose_dict, metrics)

    human = _render_human_text(profile, pose_dict, nutrition_dict, plan, suggestions, gemini_payload)

    return CombinedHealthReport(
        user_profile=profile.model_dump(),
        pose_analysis=pose_dict,
        nutrition_analysis=nutrition_dict,
        meal_plan=plan.to_dict(),
        health_risk_indicators=risks,
        recommendations=suggestions,
        gemini=gemini_payload,
        human_readable=human,
    )


def _render_human_text(
    profile: UserHealthProfile,
    pose: Dict[str, Any],
    nutrition: Dict[str, Any],
    plan: WeeklyMealPlan,
    recs: Dict[str, List[str]],
    gemini: Optional[Dict[str, Any]],
) -> str:
    lines: List[str] = []
    lines.append("=== Combined Health Intelligence Report ===")
    lines.append("")
    lines.append("User profile:")
    lines.append(f"  Age {profile.age}, goal {profile.fitness_goal.value}, activity {profile.activity_level.value}.")
    lines.append("")
    lines.append("Pose / movement:")
    lines.append(f"  Mean pose score: {pose.get('mean_pose_score', 'n/a')}")
    lines.append(f"  Injury risk (heuristic): {pose.get('injury_risk_score', 'n/a')}")
    if pose.get("summary_issues"):
        lines.append("  Issues:")
        for it in pose["summary_issues"][:6]:
            lines.append(f"    - {it}")
    if pose.get("corrections"):
        lines.append("  Corrections:")
        for it in pose["corrections"][:6]:
            lines.append(f"    - {it}")
    lines.append("")
    lines.append("Nutrition:")
    am = nutrition.get("anthropometrics", {})
    lines.append(f"  BMI {am.get('bmi')} ({am.get('bmi_category')}), target kcal {am.get('target_calories_kcal')}.")
    macros = am.get("macros", {})
    lines.append(
        f"  Macros (g): protein {macros.get('protein_g')}, carbs {macros.get('carbs_g')}, fat {macros.get('fat_g')}."
    )
    lines.append("")
    lines.append("7-day plan (summary):")
    for d in plan.to_dict()["days"][:3]:
        lines.append(f"  Day {d['day']}: {len(d['meals'])} meals, ~{d['daily_totals']['calories']:.0f} kcal.")
    lines.append("  (Full JSON includes all 7 days.)")
    lines.append("")
    lines.append("Suggestions:")
    for bucket, items in recs.items():
        lines.append(f"  [{bucket}]")
        for it in items[:5]:
            lines.append(f"    - {it}")
    if gemini and gemini.get("executive_summary"):
        lines.append("")
        lines.append("AI narrative:")
        lines.append(gemini["executive_summary"])
    return "\n".join(lines)
