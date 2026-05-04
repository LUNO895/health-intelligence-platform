# Health Intelligence Platform

Multi-module research-oriented application that merges **pose/video analysis (MediaPipe)**, a **personalized nutrition engine (BMI, BMR, TDEE, macros, 7-day meals)**, and **Gemini-powered reporting plus an explainer video pipeline** (script → gTTS → moviepy/ffmpeg).

## Layout

- `pose_module/` — `pose_detection.py`, `angle_calculation.py`, `video_analyzer.py`, `posture_classifier.py` (RandomForest on synthetic rule-labeled features), `webcam_demo.py`
- `nutrition_module/` — `bmi_bmr.py`, `meal_planner.py`, `schemas.py`
- `analysis_module/` — `report_generator.py`, `gemini_integration.py`, `pdf_export.py`
- `video_module/` — `script_generator.py`, `video_creator.py`
- `suggestion_engine/` — combined rule-based coaching
- `database/` — SQLite progress log
- `api/main.py` — FastAPI
- `streamlit_app.py` — dashboard with charts and optional video render

## Prerequisites

- **Python 3.10–3.12** recommended (MediaPipe wheels may lag on very new Python versions).
- **ffmpeg** on `PATH` for moviepy video export (`brew install ffmpeg` on macOS).

## Setup

```bash
cd "/Users/ramcharanteja/Downloads/mine/projects/ai project/health_intelligence_platform"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest  # optional, for tests
cp .env.example .env
# Edit .env and set GEMINI_API_KEY for AI sections (optional but recommended).
```

## Run API (FastAPI)

```bash
cd "/Users/ramcharanteja/Downloads/mine/projects/ai project/health_intelligence_platform"
source .venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000/docs` for interactive Swagger.

### Web UI (live camera + home page)

After `uvicorn` is running, open in your browser:

- **`http://127.0.0.1:8000/`** — home page with links (not blank).
- **`http://127.0.0.1:8000/live-pose`** — **live webcam** pose: MediaPipe runs in the browser; click **Start camera** and allow access.
- **`http://127.0.0.1:8000/nutrition-planner`** — user-friendly BMI/body-fat based nutrition planner.
- **`http://127.0.0.1:8000/daily-progress`** — daily checklist + streak calendar + live pushup/pullup camera tracker.

Do **not** double-click the HTML files in Finder/Explorer (`file://`): the WASM model and ES modules usually fail there, which looks like a **blank page**. Always use the `http://127.0.0.1:8000/...` URLs while the API is running.

### Key endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness + Gemini configured flag |
| POST | `/v1/nutrition/metrics-and-plan` | BMI/BMR/TDEE/macros + 7-day meal scaffold |
| POST | `/v1/pose/analyze-video` | Multipart video → pose metrics JSON |
| POST | `/v1/report/combined` | JSON body: `{ "profile": {…}, "pose": {…} \| null, "use_gemini": true }` |
| POST | `/v1/report/combined-with-upload` | Multipart: `file` + `profile_json` string + `use_gemini` |
| POST | `/v1/video/generate` | JSON: `{ "report": {...}, "human_text": "...", "prefer_gemini_script": true, "pose_preview_path": null }` |
| POST | `/v1/report/export-pdf` | JSON report body → `output/latest_report.pdf` |
| GET | `/download/video` | Serves `output/health_explainer.mp4` if present |
| GET | `/v1/progress/recent` | SQLite event log |

`sample_data/user_profile.json` shows the expected profile shape.

## Run Streamlit dashboard

```bash
cd "/Users/ramcharanteja/Downloads/mine/projects/ai project/health_intelligence_platform"
source .venv/bin/activate
streamlit run streamlit_app.py
```

Flow: **Nutrition** tab (build profile) → **Pose video** tab (optional upload) → **Combined + video** tab.

## Live webcam (bonus)

Requires GUI OpenCV:

```bash
pip install opencv-python  # replaces headless for camera windows
python -m pose_module.webcam_demo --camera 0
```

## Google Gemini

1. Create an API key in [Google AI Studio](https://aistudio.google.com/apikey).
2. Put it in `.env` as `GEMINI_API_KEY=...`.
3. Optional: `GEMINI_MODEL=gemini-2.0-flash` (default).

Without a key, the system still runs using deterministic nutrition math, pose heuristics, and rule-based suggestions; Gemini blocks fall back to explanatory placeholders.

## Research mapping (high level)

- **Module 1 (pose / CV paper themes):** landmark-based angles, movement heuristics, imbalance and injury-risk proxies, optional ML posture label.
- **Module 2 (dietary platform paper themes):** single-platform-style nutrition profile → energy needs → macro split → weekly meal scaffold with allergy awareness fields.
- **Module 3 (AI reporting / explanation):** Gemini merges pose + nutrition JSON into structured insights and a spoken script; `video_module` turns charts + narrative into an MP4.

## Tests

```bash
cd "/Users/ramcharanteja/Downloads/mine/projects/ai project/health_intelligence_platform"
source .venv/bin/activate
pytest -q
```

## Notes

- Outputs land in `output/` (videos, uploads, previews) and `data/health_intel.sqlite` (progress log).
- Pose scores and “injury risk” are **heuristic research demos**, not medical devices.
- gTTS requires network access the first time it synthesizes speech.
