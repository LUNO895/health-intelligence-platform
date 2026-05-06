"""FastAPI surface for pose, nutrition, combined report, and video export."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from analysis_module.pdf_export import export_combined_pdf  # noqa: E402
from analysis_module.report_generator import build_combined_report  # noqa: E402
from database.db import init_db, log_event, recent_events  # noqa: E402
from nutrition_module.bmi_bmr import compute_nutrition_metrics, metrics_to_dict  # noqa: E402
from nutrition_module.meal_planner import build_weekly_plan  # noqa: E402
from nutrition_module.schemas import UserHealthProfile  # noqa: E402
from pose_module.video_analyzer import analyze_video_file, report_to_dict  # noqa: E402
from video_module.script_generator import build_explainer_script  # noqa: E402
from video_module.video_creator import render_health_video  # noqa: E402
from cooking_module.recipes import suggest_recipes  # noqa: E402

OUTPUT = ROOT / "output"
OUTPUT.mkdir(parents=True, exist_ok=True)
STATIC_DIR = ROOT / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
init_db(ROOT / "data" / "health_intel.sqlite")


class NutritionOnlyRequest(UserHealthProfile):
    use_gemini: bool = Field(default=True)


class CombinedReportRequest(BaseModel):
    profile: UserHealthProfile
    pose: Optional[Dict[str, Any]] = None
    use_gemini: bool = True


class VideoRenderRequest(BaseModel):
    report: Dict[str, Any]
    human_text: str
    prefer_gemini_script: bool = True
    pose_preview_path: Optional[str] = None


app = FastAPI(title="Health Intelligence Platform", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve shared CSS/JS assets
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index_page() -> FileResponse:
    """Visible home page (avoid blank / when using browser)."""
    path = STATIC_DIR / "index.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="static/index.html missing")
    return FileResponse(path, media_type="text/html")


@app.get("/live-pose")
def live_pose_page() -> FileResponse:
    """Live webcam pose UI (MediaPipe in browser; requires HTTPS or localhost)."""
    path = STATIC_DIR / "live_pose.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="static/live_pose.html missing")
    return FileResponse(path, media_type="text/html")


@app.get("/nutrition-planner")
def nutrition_planner_page() -> FileResponse:
    path = STATIC_DIR / "nutrition_planner.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="static/nutrition_planner.html missing")
    return FileResponse(path, media_type="text/html")


@app.get("/daily-progress")
def daily_progress_page() -> FileResponse:
    path = STATIC_DIR / "daily_progress.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="static/daily_progress.html missing")
    return FileResponse(path, media_type="text/html")


@app.get("/cook-assistant")
def cook_assistant_page() -> FileResponse:
    path = STATIC_DIR / "cook_assistant.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="static/cook_assistant.html missing")
    return FileResponse(path, media_type="text/html")


@app.get("/yoga-mode")
def yoga_mode_page() -> FileResponse:
    path = STATIC_DIR / "yoga_mode.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="static/yoga_mode.html missing")
    return FileResponse(path, media_type="text/html")


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        "output_dir": str(OUTPUT),
        "live_pose_ui": "/live-pose",
    }


@app.post("/v1/nutrition/metrics-and-plan")
def nutrition_metrics_and_plan(req: NutritionOnlyRequest) -> Dict[str, Any]:
    profile = UserHealthProfile.model_validate(req.model_dump(exclude={"use_gemini"}))
    metrics = compute_nutrition_metrics(profile)
    plan = build_weekly_plan(profile, metrics)
    return {
        "anthropometrics": metrics_to_dict(metrics),
        "meal_plan": plan.to_dict(),
    }


@app.post("/v1/nutrition/weekly-plan")
def nutrition_weekly_plan(req: NutritionOnlyRequest) -> Dict[str, Any]:
    """
    Returns a 7-day plan with breakfast/lunch/snack/dinner.
    Intended for the Nutrition Planner UI.
    """
    profile = UserHealthProfile.model_validate(req.model_dump(exclude={"use_gemini"}))
    metrics = compute_nutrition_metrics(profile)
    plan = build_weekly_plan(profile, metrics)
    return {
        "anthropometrics": metrics_to_dict(metrics),
        "weekly_plan": plan.to_dict(),
    }


@app.post("/v1/nutrition/weekly-plan.csv", response_class=PlainTextResponse)
def nutrition_weekly_plan_csv(req: NutritionOnlyRequest) -> str:
    profile = UserHealthProfile.model_validate(req.model_dump(exclude={"use_gemini"}))
    metrics = compute_nutrition_metrics(profile)
    plan = build_weekly_plan(profile, metrics).to_dict()
    # Simple CSV
    lines = ["day,meal_type,name,calories,protein_g,carbs_g,fat_g"]
    for d in plan.get("days", []):
        day = d.get("day")
        for m in d.get("meals", []):
            lines.append(
                f'{day},{m.get("type")},{_csv_safe(m.get("name"))},{m.get("calories")},{m.get("protein_g")},{m.get("carbs_g")},{m.get("fat_g")}'
            )
    return "\n".join(lines)


def _csv_safe(v: Any) -> str:
    s = str(v or "").replace('"', '""')
    if "," in s or "\n" in s:
        return f'"{s}"'
    return s


@app.post("/v1/cook/suggest")
def cook_suggest(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Input JSON:
      { "ingredients": "rice, egg, tomato", "limit": 5 }
    """
    ingredients = payload.get("ingredients", "")
    limit = int(payload.get("limit", 5) or 5)
    return suggest_recipes(ingredients, limit=limit)

@app.post("/v1/pose/analyze-video")
async def pose_analyze_video(
    file: UploadFile = File(...),
    stride: int = Form(3),
    max_frames: int = Form(240),
) -> Dict[str, Any]:
    suffix = Path(file.filename or "upload.mp4").suffix or ".mp4"
    dest = OUTPUT / f"upload_pose{suffix}"
    dest.write_bytes(await file.read())
    try:
        rep = analyze_video_file(dest, stride=stride, max_frames=max_frames, output_dir=OUTPUT / "pose_previews")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return report_to_dict(rep)


@app.post("/v1/report/combined")
def combined_report(req: CombinedReportRequest) -> Dict[str, Any]:
    report = build_combined_report(req.profile, req.pose, use_gemini=req.use_gemini)
    log_event(
        user_label="api",
        bmi=report.nutrition_analysis.get("anthropometrics", {}).get("bmi"),
        pose_score=report.pose_analysis.get("mean_pose_score"),
        payload={"has_gemini": bool(report.gemini)},
    )
    return {
        "report_json": report.to_dict(),
        "report_human": report.human_readable,
        "gemini": report.gemini,
    }


@app.post("/v1/report/combined-with-upload")
async def combined_with_upload(
    file: UploadFile = File(...),
    profile_json: str = Form(...),
    use_gemini: bool = Form(True),
) -> Dict[str, Any]:
    profile = UserHealthProfile.model_validate(json.loads(profile_json))
    suffix = Path(file.filename or "upload.mp4").suffix or ".mp4"
    dest = OUTPUT / f"upload_full{suffix}"
    dest.write_bytes(await file.read())
    try:
        pose_rep = analyze_video_file(dest, output_dir=OUTPUT / "pose_previews")
        pose_dict = report_to_dict(pose_rep)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Pose analysis failed: {exc}") from exc

    report = build_combined_report(profile, pose_rep, use_gemini=use_gemini)
    log_event(
        user_label="api_upload",
        bmi=report.nutrition_analysis.get("anthropometrics", {}).get("bmi"),
        pose_score=pose_dict.get("mean_pose_score"),
        payload={"video": str(dest)},
    )
    return {
        "report_json": report.to_dict(),
        "report_human": report.human_readable,
        "gemini": report.gemini,
        "pose": pose_dict,
    }


@app.post("/v1/video/generate")
def generate_video(req: VideoRenderRequest) -> Dict[str, Any]:
    script = build_explainer_script(req.human_text, prefer_gemini=req.prefer_gemini_script)
    try:
        path = render_health_video(
            report_dict=req.report,
            human_text=req.human_text,
            script=script,
            out_dir=OUTPUT,
            pose_preview_path=req.pose_preview_path,
            filename="health_explainer.mp4",
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"video_path": str(path), "script": script}


@app.post("/v1/report/export-pdf")
def export_pdf(report: Dict[str, Any]) -> FileResponse:
    out = OUTPUT / "latest_report.pdf"
    try:
        export_combined_pdf(report, out)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(out, filename="health_report.pdf", media_type="application/pdf")


@app.get("/v1/progress/recent")
def progress_recent(limit: int = 20) -> JSONResponse:
    return JSONResponse({"items": recent_events(limit)})


@app.get("/download/video")
def download_video() -> FileResponse:
    p = OUTPUT / "health_explainer.mp4"
    if not p.exists():
        raise HTTPException(status_code=404, detail="Video not generated yet")
    return FileResponse(p, filename="health_explainer.mp4", media_type="video/mp4")
