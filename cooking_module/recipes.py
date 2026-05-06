"""Rule-first recipe suggestion with optional Gemini upgrade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Set


@dataclass(frozen=True)
class Recipe:
    name: str
    must_have: Set[str]
    optional: Set[str]
    steps: List[str]

    def score(self, available: Set[str]) -> float:
        if not self.must_have.issubset(available):
            return -1.0
        opt_hits = len(self.optional.intersection(available))
        return float(len(self.must_have) * 2 + opt_hits)


_RECIPES: List[Recipe] = [
    Recipe(
        name="Tomato Egg Rice Bowl",
        must_have={"rice", "egg"},
        optional={"tomato", "onion", "garlic", "pepper", "salt", "oil"},
        steps=[
            "Cook rice (or reheat cooked rice) and keep it ready.",
            "Heat 1 tsp oil. Sauté chopped onion and garlic until soft.",
            "Add chopped tomato, salt, and pepper. Cook until saucy.",
            "Scramble eggs into the sauce until set.",
            "Serve over rice. Add a squeeze of lemon if available.",
        ],
    ),
    Recipe(
        name="Quick Veg Fried Rice",
        must_have={"rice"},
        optional={"onion", "carrot", "peas", "capsicum", "egg", "soy", "garlic", "oil", "salt"},
        steps=[
            "Use cooled cooked rice for best texture.",
            "Heat oil; sauté garlic/onion. Add veggies and stir-fry 3–5 minutes.",
            "Add rice, salt, and soy (if available). Toss on high heat.",
            "Optional: scramble an egg in the pan before adding rice.",
            "Serve hot. Add chili flakes if you like spice.",
        ],
    ),
    Recipe(
        name="Onion Tomato Omelette Wrap",
        must_have={"egg"},
        optional={"onion", "tomato", "salt", "pepper", "oil", "cheese"},
        steps=[
            "Beat eggs with salt and pepper.",
            "Sauté chopped onion and tomato for 1–2 minutes.",
            "Pour eggs; cook on medium until set.",
            "Fold and serve. Optional: add cheese while folding.",
        ],
    ),
    Recipe(
        name="Tomato Onion Salad Bowl",
        must_have={"tomato", "onion"},
        optional={"lemon", "salt", "pepper", "cucumber"},
        steps=[
            "Chop tomato and onion (and cucumber if available).",
            "Season with salt and pepper; add lemon juice if available.",
            "Mix and serve as a side salad.",
        ],
    ),
]


def normalize_ingredients(text: str | List[str]) -> Set[str]:
    if isinstance(text, list):
        items = [str(x) for x in text]
    else:
        items = [t.strip() for t in str(text).replace("\n", ",").split(",")]
    out: Set[str] = set()
    for it in items:
        it = it.strip().lower()
        if not it:
            continue
        # light normalization
        it = it.replace("eggs", "egg").replace("tomatoes", "tomato").replace("onions", "onion")
        out.add(it)
    return out


def suggest_recipes(ingredients: str | List[str], limit: int = 5) -> Dict[str, Any]:
    available = normalize_ingredients(ingredients)
    scored: List[tuple[float, Recipe]] = []
    for r in _RECIPES:
        s = r.score(available)
        if s >= 0:
            scored.append((s, r))
    scored.sort(key=lambda x: -x[0])
    picks = [r for _, r in scored[:limit]]
    if not picks:
        return {
            "available": sorted(available),
            "best": None,
            "recipes": [],
            "note": "No close matches found. Add staple items like rice/egg/vegetables for better suggestions.",
        }
    best = picks[0]
    return {
        "available": sorted(available),
        "best": {
            "name": best.name,
            "ingredients_used": sorted(best.must_have.union(best.optional).intersection(available).union(best.must_have)),
            "steps": best.steps,
        },
        "recipes": [
            {
                "name": r.name,
                "ingredients_used": sorted(r.must_have.union(r.optional).intersection(available).union(r.must_have)),
                "steps": r.steps,
            }
            for r in picks
        ],
    }

