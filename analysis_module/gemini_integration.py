"""Google Gemini: combined insights, narrative, and video script."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover
    genai = None  # type: ignore


def _model_name() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def configure_gemini() -> None:
    if genai is None:
        raise RuntimeError("google-generativeai is not installed.")
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set.")
    genai.configure(api_key=key)


def generate_json(system: str, user_payload: str) -> Dict[str, Any]:
    configure_gemini()
    model = genai.GenerativeModel(_model_name())
    prompt = f"{system}\n\nDATA:\n{user_payload}\n\nRespond with valid JSON only."
    resp = model.generate_content(prompt)
    text = (resp.text or "").strip()
    if "```" in text:
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e != -1:
            text = text[s : e + 1]
    return json.loads(text)


def combined_health_insights_blob(profile_dict: Dict, pose_dict: Dict, nutrition_dict: Dict) -> Dict[str, Any]:
    system = (
        "You are a clinical-style fitness and nutrition informatics assistant. "
        "Informational only — not medical diagnosis. "
        "Return JSON keys: executive_summary (string), "
        "pose_highlights (array of strings), nutrition_highlights (array), "
        "risk_warnings (array of strings), personalized_suggestions (array), "
        "sleep_hydration_recovery (array of short strings)."
    )
    payload = json.dumps(
        {"user_profile": profile_dict, "pose_analysis": pose_dict, "nutrition_analysis": nutrition_dict},
        ensure_ascii=False,
    )
    return generate_json(system, payload)


def narrative_from_report(report_dict: Dict[str, Any]) -> str:
    configure_gemini()
    model = genai.GenerativeModel(_model_name())
    prompt = (
        "Write a clear, supportive narrative (8–12 sentences) for the end user summarizing "
        "this combined health intelligence report. Avoid alarmism; note limitations.\n\n"
        f"REPORT JSON:\n{json.dumps(report_dict, ensure_ascii=False)}"
    )
    resp = model.generate_content(prompt)
    return (resp.text or "").strip()


def gemini_video_script(report_text: str) -> str:
    configure_gemini()
    model = genai.GenerativeModel(_model_name())
    prompt = (
        "Create a spoken explainer script of ~90–130 seconds. "
        "Sections: intro, pose/movement findings, nutrition targets, risks to watch, "
        "actionable suggestions, closing encouragement. "
        "Plain sentences for TTS; no markdown bullets.\n\n"
        f"REPORT:\n{report_text}"
    )
    resp = model.generate_content(prompt)
    return (resp.text or "").strip()


def safe_gemini_call(fn, fallback: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if not os.getenv("GEMINI_API_KEY") or genai is None:
            return fallback
        return fn()
    except Exception as exc:  # noqa: BLE001
        fb = dict(fallback)
        fb["gemini_error"] = str(exc)
        return fb


def optional_insights(
    profile_dict: Dict,
    pose_dict: Dict,
    nutrition_dict: Dict,
) -> Optional[Dict[str, Any]]:
    if not os.getenv("GEMINI_API_KEY") or genai is None:
        return None
    return combined_health_insights_blob(profile_dict, pose_dict, nutrition_dict)
