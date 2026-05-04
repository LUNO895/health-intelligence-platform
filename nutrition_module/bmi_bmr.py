"""BMI, BMR (Mifflin–St Jeor + Harris–Benedict revised), TDEE, macro split."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from nutrition_module.schemas import ActivityLevel, Gender, UserHealthProfile


ACTIVITY_FACTORS: Dict[ActivityLevel, float] = {
    ActivityLevel.sedentary: 1.2,
    ActivityLevel.light: 1.375,
    ActivityLevel.moderate: 1.55,
    ActivityLevel.active: 1.725,
    ActivityLevel.very_active: 1.9,
}


def compute_bmi(weight_kg: float, height_cm: float) -> float:
    h_m = height_cm / 100.0
    return weight_kg / (h_m * h_m)


def bmi_health_classification(bmi: float) -> str:
    if bmi < 18.5:
        return "underweight"
    if bmi < 25:
        return "normal_weight"
    if bmi < 30:
        return "overweight"
    return "obese"


def bmr_mifflin_st_jeor(profile: UserHealthProfile) -> float:
    s = 5 if profile.gender == Gender.male else -161
    if profile.gender == Gender.other:
        s = (5 + (-161)) / 2
    return 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age + s


def bmr_harris_benedict_revised(profile: UserHealthProfile) -> float:
    w, h, age = profile.weight_kg, profile.height_cm, profile.age
    if profile.gender == Gender.male:
        return 88.362 + 13.397 * w + 4.799 * h - 5.677 * age
    if profile.gender == Gender.female:
        return 447.593 + 9.247 * w + 3.098 * h - 4.330 * age
    m = 88.362 + 13.397 * w + 4.799 * h - 5.677 * age
    f = 447.593 + 9.247 * w + 3.098 * h - 4.330 * age
    return (m + f) / 2.0


def compute_tdee(bmr: float, activity: ActivityLevel) -> float:
    return bmr * ACTIVITY_FACTORS[activity]


def goal_adjusted_calories(tdee: float, goal) -> float:
    from nutrition_module.schemas import FitnessGoal

    if goal == FitnessGoal.fat_loss:
        return tdee * 0.82
    if goal == FitnessGoal.muscle_gain:
        return tdee * 1.12
    return tdee * 1.0


def macro_targets(calories: float, goal, weight_kg: float) -> Dict[str, float]:
    from nutrition_module.schemas import FitnessGoal

    if goal == FitnessGoal.muscle_gain:
        protein_g = 1.9 * weight_kg
        fat_ratio = 0.28
    elif goal == FitnessGoal.fat_loss:
        protein_g = 1.8 * weight_kg
        fat_ratio = 0.30
    else:
        protein_g = 1.6 * weight_kg
        fat_ratio = 0.30

    protein_kcal = protein_g * 4.0
    fat_kcal = calories * fat_ratio
    fat_g = fat_kcal / 9.0
    carb_kcal = max(calories - protein_kcal - fat_kcal, 0.0)
    carb_g = carb_kcal / 4.0

    return {
        "calories": round(calories, 0),
        "protein_g": round(protein_g, 1),
        "carbs_g": round(carb_g, 1),
        "fat_g": round(fat_g, 1),
        "protein_pct": round(100 * protein_kcal / calories, 1) if calories else 0.0,
        "carbs_pct": round(100 * carb_kcal / calories, 1) if calories else 0.0,
        "fat_pct": round(100 * fat_kcal / calories, 1) if calories else 0.0,
    }


def likely_deficiencies(profile: UserHealthProfile, macros: Dict[str, float]) -> list[str]:
    """Heuristic micronutrient watchlist (informational, not diagnostic)."""
    notes: list[str] = []
    if profile.diet_preference.value in ("vegan", "vegetarian"):
        notes.append("Monitor B12, iron, zinc, and omega-3 intake with plant-forward patterns.")
    if macros.get("carbs_g", 0) < 80:
        notes.append("Very low carbohydrate intake — watch fiber and training fueling.")
    if profile.fitness_goal.value == "muscle_gain" and macros.get("protein_g", 0) < 1.4 * profile.weight_kg:
        notes.append("Protein may be below aggressive hypertrophy targets — consider spacing feeds.")
    if not notes:
        notes.append("No major heuristic flags — maintain varied whole foods.")
    return notes


@dataclass
class NutritionMetrics:
    bmi: float
    bmi_category: str
    bmr_mifflin: float
    bmr_harris: float
    tdee: float
    target_calories: float
    macros: Dict[str, float]
    deficiencies: list[str]
    healthy_weight_range_kg: Tuple[float, float]


def compute_nutrition_metrics(profile: UserHealthProfile) -> NutritionMetrics:
    bmi = compute_bmi(profile.weight_kg, profile.height_cm)
    cat = bmi_health_classification(bmi)
    bmr_msj = bmr_mifflin_st_jeor(profile)
    bmr_hb = bmr_harris_benedict_revised(profile)
    tdee = compute_tdee(bmr_msj, profile.activity_level)
    target_kcal = goal_adjusted_calories(tdee, profile.fitness_goal)
    macros = macro_targets(target_kcal, profile.fitness_goal, profile.weight_kg)
    defs = likely_deficiencies(profile, macros)
    h_m = profile.height_cm / 100.0
    w_low, w_high = 18.5 * h_m * h_m, 24.9 * h_m * h_m
    return NutritionMetrics(
        bmi=round(bmi, 2),
        bmi_category=cat,
        bmr_mifflin=round(bmr_msj, 1),
        bmr_harris=round(bmr_hb, 1),
        tdee=round(tdee, 1),
        target_calories=round(target_kcal, 1),
        macros=macros,
        deficiencies=defs,
        healthy_weight_range_kg=(round(w_low, 1), round(w_high, 1)),
    )


def metrics_to_dict(m: NutritionMetrics) -> Dict:
    return {
        "bmi": m.bmi,
        "bmi_category": m.bmi_category,
        "bmr_mifflin_st_jeor_kcal": m.bmr_mifflin,
        "bmr_harris_benedict_kcal": m.bmr_harris,
        "tdee_kcal": m.tdee,
        "target_calories_kcal": m.target_calories,
        "macros": m.macros,
        "nutritional_deficiency_watchlist": m.deficiencies,
        "healthy_weight_range_kg": {
            "low": m.healthy_weight_range_kg[0],
            "high": m.healthy_weight_range_kg[1],
        },
    }
