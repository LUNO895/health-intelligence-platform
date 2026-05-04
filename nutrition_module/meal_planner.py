"""Rule-based 7-day meal plan scaffold scaled to calorie and diet preference."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from nutrition_module.bmi_bmr import NutritionMetrics
from nutrition_module.schemas import DietPreference, UserHealthProfile


@dataclass
class MealItem:
    meal_type: str
    name: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


@dataclass
class DayPlan:
    day: int
    meals: List[MealItem]

    def totals(self) -> Dict[str, float]:
        k = p = c = f = 0.0
        for m in self.meals:
            k += m.calories
            p += m.protein_g
            c += m.carbs_g
            f += m.fat_g
        return {"calories": k, "protein_g": p, "carbs_g": c, "fat_g": f}


@dataclass
class WeeklyMealPlan:
    days: List[DayPlan]
    target_calories: float
    diet: DietPreference

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "diet_preference": self.diet.value,
            "target_daily_calories": self.target_calories,
            "days": [],
        }
        for d in self.days:
            out["days"].append(
                {
                    "day": d.day,
                    "meals": [
                        {
                            "type": m.meal_type,
                            "name": m.name,
                            "calories": round(m.calories, 1),
                            "protein_g": round(m.protein_g, 1),
                            "carbs_g": round(m.carbs_g, 1),
                            "fat_g": round(m.fat_g, 1),
                        }
                        for m in d.meals
                    ],
                    "daily_totals": {k: round(v, 1) for k, v in d.totals().items()},
                }
            )
        return out


def _base_templates(diet: DietPreference) -> Dict[str, List[MealItem]]:
    if diet == DietPreference.vegan:
        breakfast = [
            MealItem("breakfast", "Oatmeal + berries + flax", 420, 14, 68, 10),
            MealItem("breakfast", "Tofu scramble + wholegrain toast", 450, 22, 48, 16),
        ]
        lunch = [
            MealItem("lunch", "Chickpea bowl + greens + tahini", 580, 24, 78, 18),
            MealItem("lunch", "Lentil soup + quinoa side", 560, 26, 82, 12),
        ]
        dinner = [
            MealItem("dinner", "Tempeh stir-fry + brown rice", 640, 32, 72, 22),
            MealItem("dinner", "Bean chili + baked sweet potato", 620, 28, 88, 14),
        ]
        snack = [MealItem("snack", "Protein smoothie (pea protein)", 220, 20, 22, 5)]
    elif diet == DietPreference.vegetarian:
        breakfast = [
            MealItem("breakfast", "Greek yogurt parfait + fruit", 380, 22, 48, 10),
            MealItem("breakfast", "Paneer + roti + veg", 460, 24, 46, 18),
        ]
        lunch = [
            MealItem("lunch", "Dal + rice + salad", 600, 22, 90, 14),
            MealItem("lunch", "Hummus wrap + soup", 560, 18, 72, 20),
        ]
        dinner = [
            MealItem("dinner", "Grilled paneer + millet + veg", 660, 34, 70, 24),
            MealItem("dinner", "Egg curry + chapati", 640, 32, 62, 26),
        ]
        snack = [MealItem("snack", "Cottage cheese + fruit", 200, 18, 18, 6)]
    elif diet == DietPreference.keto:
        breakfast = [
            MealItem("breakfast", "Eggs + avocado + cheese", 520, 28, 12, 42),
            MealItem("breakfast", "Greek yogurt + nuts (low carb)", 440, 24, 14, 34),
        ]
        lunch = [
            MealItem("lunch", "Chicken salad + olive oil", 620, 46, 14, 44),
            MealItem("lunch", "Salmon + greens + butter", 640, 40, 10, 48),
        ]
        dinner = [
            MealItem("dinner", "Steak + broccoli + butter", 700, 48, 12, 52),
            MealItem("dinner", "Paneer tikka + greens", 660, 36, 16, 50),
        ]
        snack = [MealItem("snack", "Cheese + olives", 240, 14, 4, 20)]
    else:
        breakfast = [
            MealItem("breakfast", "Eggs + oats + fruit", 450, 26, 52, 14),
            MealItem("breakfast", "Chicken sandwich + milk", 480, 30, 48, 16),
        ]
        lunch = [
            MealItem("lunch", "Chicken rice bowl + veg", 680, 42, 78, 18),
            MealItem("lunch", "Fish + potatoes + salad", 660, 38, 70, 22),
        ]
        dinner = [
            MealItem("dinner", "Mutton/chicken curry + rice", 720, 44, 82, 20),
            MealItem("dinner", "Grilled fish + quinoa", 700, 40, 74, 24),
        ]
        snack = [MealItem("snack", "Protein bar + fruit", 260, 18, 28, 8)]

    return {"breakfast": breakfast, "lunch": lunch, "dinner": dinner, "snack": snack}


def _scale_meals(meals: List[MealItem], factor: float) -> List[MealItem]:
    out: List[MealItem] = []
    for m in meals:
        out.append(
            MealItem(
                m.meal_type,
                m.name,
                m.calories * factor,
                m.protein_g * factor,
                m.carbs_g * factor,
                m.fat_g * factor,
            )
        )
    return out


def build_weekly_plan(profile: UserHealthProfile, metrics: NutritionMetrics) -> WeeklyMealPlan:
    templates = _base_templates(profile.diet_preference)
    target = metrics.target_calories
    days: List[DayPlan] = []

    for day in range(7):
        picked: List[MealItem] = []
        for key in ("breakfast", "lunch", "snack", "dinner"):
            pool = templates.get(key, [])
            if not pool:
                continue
            picked.append(pool[day % len(pool)])

        base_kcal = sum(m.calories for m in picked) or 1.0
        scale = float(target) / base_kcal
        scale = max(0.75, min(scale, 1.35))
        scaled = _scale_meals(picked, scale)
        days.append(DayPlan(day=day + 1, meals=scaled))

    return WeeklyMealPlan(days=days, target_calories=target, diet=profile.diet_preference)
