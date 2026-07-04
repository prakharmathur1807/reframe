"""Ingest stage — validate and probe the source video.

Runs ffprobe on the file already placed in the job temp dir and populates
the JobContext with duration, resolution, and fps. Raises ``ValueError``
for files that are too long, too short, or not valid video.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ..config import settings
from .context import JobContext

STAGE = "ingest"

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
MIN_DURATION = 5.0   # seconds — anything shorter is probably a test artefact
MAX_DURATION = float(settings.max_video_duration_seconds)


def run(ctx: JobContext) -> None:
    ctx.progress(STAGE, 0.0, "Probing video…")

    path = ctx.source_path
    if path is None or not path.exists():
        raise ValueError("Source video file not found")

    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported format '{path.suffix}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    if path.stat().st_size > settings.max_upload_bytes:
        raise ValueError(
            f"File exceeds the {settings.max_upload_bytes // (1024**3)} GiB limit"
        )

    ctx.progress(STAGE, 30.0, "Reading stream metadata…")
    info = _ffprobe(path)

    streams = info.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    if not video_streams:
        raise ValueError("No video stream found in the file")

    vs = video_streams[0]
    fmt = info.get("format", {})

    duration = float(fmt.get("duration") or vs.get("duration") or 0)
    if duration < MIN_DURATION:
        raise ValueError(f"Video is too short ({duration:.1f}s — minimum {MIN_DURATION}s)")
    if duration > MAX_DURATION:
        raise ValueError(
            f"Video is {duration / 3600:.2f}h — maximum is "
            f"{settings.max_video_duration_seconds // 3600}h"
        )

    # Parse FPS from "num/den" string
    fps_raw = vs.get("r_frame_rate", "25/1")
    try:
        num, den = fps_raw.split("/")
        fps = float(num) / float(den)
    except Exception:
        fps = 25.0

    ctx.duration_seconds = duration
    ctx.width = int(vs.get("width", 0))
    ctx.height = int(vs.get("height", 0))
    ctx.fps = round(fps, 3)

    ctx.artifacts["video_path"] = str(path)
    ctx.artifacts["duration"] = duration
    ctx.artifacts["width"] = ctx.width
    ctx.artifacts["height"] = ctx.height
    ctx.artifacts["fps"] = ctx.fps

    ctx.progress(
        STAGE,
        100.0,
        f"Probed: {ctx.width}×{ctx.height} @ {ctx.fps:.2f}fps · "
        f"{duration:.1f}s",
    )


def _ffprobe(path: Path) -> dict:
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=True
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"ffprobe failed: {exc.stderr.strip()[:200]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ValueError("ffprobe timed out probing the file") from exc

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"ffprobe returned unexpected output: {exc}") from exc
