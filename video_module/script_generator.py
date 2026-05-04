"""Report → spoken script (Gemini when available)."""

from __future__ import annotations

import os

from analysis_module import gemini_integration


def build_explainer_script(human_readable_report: str, *, prefer_gemini: bool = True) -> str:
    if prefer_gemini and os.getenv("GEMINI_API_KEY"):
        try:
            return gemini_integration.gemini_video_script(human_readable_report[:6000])
        except Exception:  # noqa: BLE001
            pass
    return (
        "Welcome to your personalized health briefing. "
        "This video summarizes movement quality, nutrition targets, and daily habits. "
        + human_readable_report[:1200].replace("\n", " ")
    )
