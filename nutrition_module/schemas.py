"""User intake models for the nutrition engine."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class ActivityLevel(str, Enum):
    sedentary = "sedentary"
    light = "light"
    moderate = "moderate"
    active = "active"
    very_active = "very_active"


class FitnessGoal(str, Enum):
    fat_loss = "fat_loss"
    muscle_gain = "muscle_gain"
    maintenance = "maintenance"


class DietPreference(str, Enum):
    vegetarian = "vegetarian"
    vegan = "vegan"
    non_vegetarian = "non_vegetarian"
    keto = "keto"


class UserHealthProfile(BaseModel):
    age: int = Field(..., ge=14, le=100)
    gender: Gender
    height_cm: float = Field(..., ge=100, le=250)
    weight_kg: float = Field(..., ge=30, le=300)
    activity_level: ActivityLevel
    fitness_goal: FitnessGoal
    diet_preference: DietPreference
    allergies: List[str] = Field(default_factory=list)
    medical_notes: Optional[str] = Field(default=None, description="Informational context only.")

    @field_validator("allergies", mode="before")
    @classmethod
    def normalize_allergies(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [a.strip() for a in v.split(",") if a.strip()]
        return [str(x).strip() for x in v]
