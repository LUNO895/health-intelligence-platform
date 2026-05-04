"""Anthropometrics, energy needs, and meal planning (Module 2)."""

from nutrition_module.bmi_bmr import NutritionMetrics, compute_nutrition_metrics
from nutrition_module.meal_planner import WeeklyMealPlan, build_weekly_plan
from nutrition_module.schemas import ActivityLevel, DietPreference, FitnessGoal, Gender, UserHealthProfile

__all__ = [
    "NutritionMetrics",
    "compute_nutrition_metrics",
    "WeeklyMealPlan",
    "build_weekly_plan",
    "ActivityLevel",
    "DietPreference",
    "FitnessGoal",
    "Gender",
    "UserHealthProfile",
]
