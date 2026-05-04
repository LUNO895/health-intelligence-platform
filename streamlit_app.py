"""Dashboard: pose upload, nutrition, combined report, charts, optional video."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis_module.report_generator import build_combined_report  # noqa: E402
from database.db import init_db, log_event, recent_events  # noqa: E402
from nutrition_module.bmi_bmr import compute_nutrition_metrics, metrics_to_dict  # noqa: E402
from nutrition_module.meal_planner import build_weekly_plan  # noqa: E402
from nutrition_module.schemas import (  # noqa: E402
    ActivityLevel,
    DietPreference,
    FitnessGoal,
    Gender,
    UserHealthProfile,
)
from pose_module.video_analyzer import analyze_video_file, report_to_dict  # noqa: E402
from video_module.script_generator import build_explainer_script  # noqa: E402
from video_module.video_creator import render_health_video  # noqa: E402

st.set_page_config(page_title="Health Intelligence", layout="wide")
init_db(ROOT / "data" / "health_intel.sqlite")

st.title("Research-Driven Health Intelligence Platform")
st.caption("Modules: Pose (MediaPipe) · Nutrition engine · Gemini analysis & explainer video")
st.info(
    "**Live webcam pose (recommended):** run the API in another terminal "
    "(`uvicorn api.main:app --port 8000`), then open "
    "**http://127.0.0.1:8000/live-pose** "
    "or **http://127.0.0.1:8000/** for the home page. "
    "Opening the `.html` file from disk (`file://`) often stays **blank** because the model must load over HTTP."
)

tab_live, tab_pose, tab_nut, tab_full = st.tabs(
    ["Live pose (browser)", "Pose video upload", "Nutrition", "Combined + video"]
)

with tab_live:
    st.subheader("Real-time camera pose")
    st.markdown(
        "Streamlit cannot access your webcam the same way a browser tab does for this demo. "
        "Use the FastAPI-hosted page for **continuous** pose tracking."
    )
    try:
        st.link_button("Open live pose page", "http://127.0.0.1:8000/live-pose")
    except Exception:
        st.markdown("[Open live pose page](http://127.0.0.1:8000/live-pose)")
    st.markdown(
        "- Start API: `uvicorn api.main:app --host 127.0.0.1 --port 8000`\n"
        "- Click **Start camera** on that page and allow the camera.\n"
        "- Wait for the model download on first visit."
    )

with tab_pose:
    st.subheader("Module 1 — Pose & movement")
    up = st.file_uploader("Upload MP4/MOV (short clips work best)", type=["mp4", "mov", "avi"])
    stride = st.slider("Frame stride (higher = faster)", 1, 10, 3)
    if up and st.button("Analyze pose"):
        tmp = ROOT / "output" / up.name
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(up.getbuffer())
        with st.spinner("Running MediaPipe pose pipeline…"):
            rep = analyze_video_file(tmp, stride=stride, output_dir=ROOT / "output" / "pose_previews")
        st.session_state["last_pose"] = report_to_dict(rep)
        st.success("Analysis complete")
    if st.session_state.get("last_pose"):
        lp = st.session_state["last_pose"]
        st.metric("Mean pose score", lp.get("mean_pose_score"))
        c1, c2, c3 = st.columns(3)
        c1.metric("Injury risk (heuristic)", lp.get("injury_risk_score"))
        c2.metric("Imbalance proxy", lp.get("imbalance_score"))
        c3.metric("Pose coverage", lp.get("pose_coverage"))
        st.bar_chart(
            {
                "pose_score": [lp.get("mean_pose_score") or 0],
                "injury_risk": [lp.get("injury_risk_score") or 0],
            }
        )
        st.write("Issues:", lp.get("summary_issues"))
        st.write("Corrections:", lp.get("corrections"))
        if lp.get("preview_frame_path") and Path(lp["preview_frame_path"]).exists():
            st.image(lp["preview_frame_path"], caption="Annotated preview (worst early frame)")

with tab_nut:
    st.subheader("Module 2 — Nutrition & health engine")
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age", 16, 90, 28)
        gender = st.selectbox("Gender", [e.value for e in Gender])
        h = st.number_input("Height (cm)", 120.0, 220.0, 172.0)
        w = st.number_input("Weight (kg)", 40.0, 180.0, 72.0)
    with col2:
        act = st.selectbox("Activity", [e.value for e in ActivityLevel])
        goal = st.selectbox("Goal", [e.value for e in FitnessGoal])
        diet = st.selectbox("Diet preference", [e.value for e in DietPreference])
        allergies = st.text_input("Allergies (comma-separated)", "")

    if st.button("Compute metrics + 7-day plan"):
        profile = UserHealthProfile(
            age=int(age),
            gender=Gender(gender),
            height_cm=float(h),
            weight_kg=float(w),
            activity_level=ActivityLevel(act),
            fitness_goal=FitnessGoal(goal),
            diet_preference=DietPreference(diet),
            allergies=[a.strip() for a in allergies.split(",") if a.strip()],
        )
        metrics = compute_nutrition_metrics(profile)
        plan = build_weekly_plan(profile, metrics)
        st.session_state["last_profile"] = profile
        st.session_state["last_metrics"] = metrics_to_dict(metrics)
        st.session_state["last_plan"] = plan.to_dict()
        log_event(user_label="streamlit", bmi=metrics.bmi, pose_score=None, payload={"goal": goal})

    if st.session_state.get("last_metrics"):
        m = st.session_state["last_metrics"]
        st.json(m)
        st.write("7-day meal plan")
        st.json(st.session_state["last_plan"])

with tab_full:
    st.subheader("Module 3 — Combined report, Gemini, explainer video")
    if not st.session_state.get("last_profile"):
        st.info("Set a nutrition profile in the Nutrition tab first (or defaults will be used).")
    use_gem = st.checkbox("Use Gemini for merged insights (needs GEMINI_API_KEY)", value=True)
    gen_vid = st.checkbox("Render explainer video (needs ffmpeg + internet for gTTS)", value=False)

    if st.button("Build combined report"):
        profile: UserHealthProfile = st.session_state.get(
            "last_profile",
            UserHealthProfile(
                age=28,
                gender=Gender.male,
                height_cm=172,
                weight_kg=72,
                activity_level=ActivityLevel.moderate,
                fitness_goal=FitnessGoal.maintenance,
                diet_preference=DietPreference.non_vegetarian,
                allergies=[],
            ),
        )
        pose = st.session_state.get("last_pose")
        with st.spinner("Merging pose + nutrition + suggestions…"):
            report = build_combined_report(profile, pose, use_gemini=use_gem)
        st.session_state["combined_report"] = report.to_dict()
        st.session_state["combined_human"] = report.human_readable
        st.success("Report ready")
        st.text_area("Human-readable", report.human_readable, height=260)
        st.json(report.to_dict())
        if report.gemini:
            st.subheader("Gemini merged insights")
            st.json(report.gemini)

        if gen_vid:
            with st.spinner("Rendering video (may take a minute)…"):
                script = build_explainer_script(report.human_readable, prefer_gemini=use_gem)
                preview = (pose or {}).get("preview_frame_path") if pose else None
                vp = render_health_video(
                    report_dict=report.to_dict(),
                    human_text=report.human_readable,
                    script=script,
                    out_dir=ROOT / "output",
                    pose_preview_path=preview,
                )
            st.video(str(vp))
            st.caption(f"Saved to `{vp}`")

    st.subheader("Progress log (SQLite)")
    st.json({"recent": recent_events(10)})
