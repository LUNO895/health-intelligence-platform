"""Charts + optional pose still + TTS voiceover via moviepy/ffmpeg."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from gtts import gTTS
from moviepy import concatenate_audioclips, concatenate_videoclips
from moviepy.audio.AudioClip import AudioClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import ImageClip

try:
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover
    plt = None


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _tts_to_file(script: str, out_mp3: Path) -> None:
    chunks: List[str] = textwrap.wrap(script.replace("\n", " "), 900) or ["No script."]
    if len(chunks) == 1:
        gTTS(chunks[0], lang="en", slow=False).save(str(out_mp3))
        return
    parts: List[Path] = []
    for i, ch in enumerate(chunks):
        p = out_mp3.with_name(f"{out_mp3.stem}_p{i}.mp3")
        gTTS(ch, lang="en", slow=False).save(str(p))
        parts.append(p)
    clips = [AudioFileClip(str(p)) for p in parts]
    merged = concatenate_audioclips(clips)
    merged.write_audiofile(str(out_mp3), fps=44100, nbytes=2, logger=None)
    for c in clips:
        c.close()
    merged.close()
    for p in parts:
        try:
            p.unlink()
        except OSError:
            pass


def _macro_chart(macros: Dict[str, Any], out: Path) -> None:
    if plt is None:
        raise RuntimeError("matplotlib required for video charts")
    labels = ["Protein %", "Carbs %", "Fat %"]
    vals = [macros.get("protein_pct", 0), macros.get("carbs_pct", 0), macros.get("fat_pct", 0)]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, vals, color=["#4C78A8", "#F58518", "#54A24B"])
    ax.set_ylim(0, 100)
    ax.set_title("Target macro split")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def _bmi_chart(bmi: float, out: Path) -> None:
    if plt is None:
        raise RuntimeError("matplotlib required for video charts")
    fig, ax = plt.subplots(figsize=(6, 1.4))
    ax.barh([0], [30], color="#eee")
    ax.barh([0], [18.5], left=0, color="#54A24B")
    ax.barh([0], [6.5], left=18.5, color="#F58518")
    ax.barh([0], [5], left=25, color="#E45756")
    ax.scatter([bmi], [0], color="black", zorder=5)
    ax.set_xlim(10, 40)
    ax.set_yticks([])
    ax.set_xlabel("BMI")
    ax.set_title(f"BMI marker: {bmi:.1f}")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def _title_card(text: str, out: Path, title: str) -> None:
    if plt is None:
        raise RuntimeError("matplotlib required for video charts")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axis("off")
    ax.text(0.02, 0.95, title, fontsize=16, fontweight="bold", va="top", color="#eaeaea")
    ax.text(0.02, 0.85, textwrap.fill(text, 96), va="top", ha="left", fontsize=11, color="#f2f2f2")
    fig.patch.set_facecolor("#111111")
    ax.set_facecolor("#111111")
    fig.tight_layout()
    fig.savefig(out, dpi=150, facecolor="#111111")
    plt.close(fig)


def render_health_video(
    *,
    report_dict: Dict[str, Any],
    human_text: str,
    script: str,
    out_dir: str | Path,
    pose_preview_path: Optional[str] = None,
    filename: str = "health_explainer.mp4",
) -> Path:
    """
    Builds: macro chart → BMI chart → optional pose still → text body with voiceover.
    """
    out = Path(out_dir)
    _ensure_dir(out)
    tmp = out / "_tmp_video"
    _ensure_dir(tmp)

    macros = report_dict.get("nutrition_analysis", {}).get("anthropometrics", {}).get("macros", {})
    bmi = float(report_dict.get("nutrition_analysis", {}).get("anthropometrics", {}).get("bmi", 22))

    macro_png = tmp / "macros.png"
    bmi_png = tmp / "bmi.png"
    _macro_chart(macros, macro_png)
    _bmi_chart(bmi, bmi_png)

    size = (1280, 720)
    intro_clips = [
        ImageClip(str(macro_png), duration=3.5).resized(new_size=size),
        ImageClip(str(bmi_png), duration=3.5).resized(new_size=size),
    ]
    if pose_preview_path and Path(pose_preview_path).exists():
        intro_clips.insert(
            2,
            ImageClip(str(pose_preview_path), duration=3.5).resized(new_size=size),
        )
    intro = concatenate_videoclips(intro_clips, method="compose")

    audio_mp3 = tmp / "voice.mp3"
    _tts_to_file(script, audio_mp3)
    voice = AudioFileClip(str(audio_mp3))
    dur = float(voice.duration)

    pose_lines = report_dict.get("pose_analysis", {})
    pose_bit = "Pose score: {}. Risk heuristic: {}.".format(
        pose_lines.get("mean_pose_score", "n/a"),
        pose_lines.get("injury_risk_score", "n/a"),
    )
    body_png = tmp / "body.png"
    _title_card(pose_bit + "\n\n" + human_text[:2200], body_png, "Health Intelligence Brief")

    body = ImageClip(str(body_png), duration=max(dur, 4.0)).resized(new_size=size)
    video = concatenate_videoclips([intro, body], method="compose")

    silence = AudioClip(
        lambda _t: np.array([0.0, 0.0], dtype=float),
        duration=float(intro.duration),
        fps=44100,
    )
    combined_audio = concatenate_audioclips([silence, voice])
    final = video.with_audio(combined_audio).with_fps(24)

    out_path = out / filename
    final.write_videofile(
        str(out_path),
        fps=24,
        codec="libx264",
        audio_codec="aac",
        threads=2,
        preset="veryfast",
        logger=None,
    )
    final.close()
    voice.close()
    combined_audio.close()
    silence.close()
    return out_path
