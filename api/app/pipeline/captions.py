"""Caption engine — generate .ass subtitles with karaoke word timing.

Supports multiple visual styles:
  - default: white text, black stroke, no background
  - karaoke: word-by-word highlight (yellow → white)
  - boxed: white text on semi-transparent black background
  - emoji: like default but appends auto-selected emoji per segment

The .ass file is burned into the video by the render stage.
"""

from __future__ import annotations

import re
from pathlib import Path

from .context import JobContext

STAGE = "captions"

# ── ASS Style definitions ──────────────────────────────────────────────────
_STYLES = {
    "default": (
        "Style: Default,Arial,52,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
        "0,0,0,0,100,100,0,0,1,3,1,2,20,20,60,1"
    ),
    "karaoke": (
        "Style: Default,Arial Bold,56,&H00FFFFFF,&H0000FFFF,&H00000000,&H90000000,"
        "0,0,0,0,100,100,0,0,1,3,1,2,20,20,60,1"
    ),
    "boxed": (
        "Style: Default,Arial Bold,52,&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,"
        "0,0,0,0,100,100,0,0,1,0,0,2,20,20,60,1"
    ),
}

_EMOJI_MAP = {
    "laugh": "😂", "funny": "😄", "wow": "😮", "amazing": "🔥",
    "love": "❤️", "great": "✅", "money": "💰", "learn": "📚",
    "win": "🏆", "run": "🏃", "ai": "🤖", "secret": "🤫",
}


def run(ctx: JobContext, style: str = "karaoke") -> None:
    ctx.progress(STAGE, 0.0, "Generating captions…")

    segments: list[dict] = ctx.require_artifact("segments")
    words: list[dict] = ctx.require_artifact("words")
    ass_path = ctx.artifact_path("captions.ass")

    ass_content = _build_ass(segments, style=style)
    ass_path.write_text(ass_content, encoding="utf-8")

    ctx.artifacts["ass_path"] = str(ass_path)
    ctx.progress(STAGE, 100.0, f"Captions ready — {len(segments)} lines, style={style}")


def _build_ass(segments: list[dict], style: str = "karaoke") -> str:
    style_def = _STYLES.get(style, _STYLES["default"])

    header = f"""\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_def}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    lines = [header]
    for seg in segments:
        start_tc = _tc(seg["start"])
        end_tc = _tc(seg["end"])

        if style == "karaoke":
            text = _karaoke_line(seg)
        else:
            text = _clean(seg["text"])
            if style == "emoji":
                text = text + " " + _pick_emoji(seg["text"])

        lines.append(f"Dialogue: 0,{start_tc},{end_tc},Default,,0,0,0,,{text}")

    return "\n".join(lines)


def _tc(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    cs = int((s % 1) * 100)
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"


def _karaoke_line(seg: dict) -> str:
    """Build karaoke override tags for word-by-word reveal."""
    parts: list[str] = []
    prev_end = seg["start"]
    for w in seg.get("words", []):
        dur_cs = max(1, int((w["end"] - w["start"]) * 100))
        gap_cs = max(0, int((w["start"] - prev_end) * 100))
        if gap_cs > 0:
            parts.append(f"{{\\k{gap_cs}}}")
        parts.append(f"{{\\kf{dur_cs}}}{_clean(w['word'])}")
        prev_end = w["end"]
    return "".join(parts)


def _clean(text: str) -> str:
    return re.sub(r"[{}\[\]]", "", text).strip()


def _pick_emoji(text: str) -> str:
    t = text.lower()
    for kw, emoji in _EMOJI_MAP.items():
        if kw in t:
            return emoji
    return ""
