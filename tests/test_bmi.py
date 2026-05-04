from nutrition_module.schemas import (
    ActivityLevel,
    DietPreference,
    FitnessGoal,
    Gender,
    UserHealthProfile,
)
from nutrition_module.bmi_bmr import compute_bmi, compute_nutrition_metrics


def test_bmi():
    assert abs(compute_bmi(70, 175) - 22.86) < 0.1


def test_pipeline_smoke():
    p = UserHealthProfile(
        age=29,
        gender=Gender.male,
        height_cm=178,
        weight_kg=80,
        activity_level=ActivityLevel.active,
        fitness_goal=FitnessGoal.muscle_gain,
        diet_preference=DietPreference.non_vegetarian,
        allergies=[],
    )
    m = compute_nutrition_metrics(p)
    assert m.target_calories > 0
    assert m.macros["protein_g"] > 0
