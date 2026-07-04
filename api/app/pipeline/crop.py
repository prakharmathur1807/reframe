"""Crop planning stage — compute a smooth 9:16 virtual-camera path.

Algorithm:
1. For each sampled frame, pick the target face centre (active speaker first,
   else largest face, else frame centre).
2. Apply a dead-zone filter: only move the virtual camera when the subject
   leaves a tolerance box — avoids micro-jitter.
3. Smooth the resulting keyframe sequence with Savitzky-Golay.
4. Clamp every crop rect so it never goes outside the source frame.

Output artifact ``crop_plan``:
  [{"frame": int, "time": float, "x": int, "y": int, "w": int, "h": int}]
  where (x, y, w, h) is the crop window in source-video pixels.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import savgol_filter  # type: ignore[import]

from .context import JobContext

STAGE = "crop"
TARGET_ASPECT = 9 / 16
DEAD_ZONE_RATIO = 0.08    # subject must leave this fraction of crop width before camera moves
SAVGOL_WINDOW = 31        # must be odd; larger = smoother
SAVGOL_POLY = 3


def run(ctx: JobContext) -> None:
    ctx.progress(STAGE, 0.0, "Planning 9:16 crop path…")

    src_w: int = ctx.require_artifact("width")
    src_h: int = ctx.require_artifact("height")
    fps: float = ctx.artifacts.get("fps", 25.0)
    face_detections: list[dict] = ctx.require_artifact("face_detections")
    timeline: list[dict] = ctx.artifacts.get("active_speaker_timeline", [])
    primary_tid: int | None = ctx.artifacts.get("primary_speaker_track")

    # Determine crop window size (9:16 inside the source frame)
    crop_h = src_h
    crop_w = int(crop_h * TARGET_ASPECT)
    if crop_w > src_w:
        crop_w = src_w
        crop_h = int(crop_w / TARGET_ASPECT)

    # Build a speaker lookup: time → track_id
    spk_lookup: dict[float, int | None] = {
        round(e["time"], 2): e["track_id"] for e in timeline
    }

    # Build face lookup: frame → list of face dicts (with track_id if present)
    face_by_frame: dict[int, list[dict]] = {}
    for fd in face_detections:
        face_by_frame[fd["frame"]] = fd.get("faces", [])

    # Raw target centre-x per sampled frame
    raw_cx: list[float] = []
    frame_times: list[float] = []

    for fd in face_detections:
        frame_idx = fd["frame"]
        t = fd["time"]
        faces = fd.get("faces", [])

        target_cx = _pick_target_cx(faces, t, spk_lookup, primary_tid, src_w)
        raw_cx.append(target_cx)
        frame_times.append(t)

    ctx.progress(STAGE, 40.0, "Smoothing camera path…")

    if not raw_cx:
        # No faces at all — centre crop throughout
        raw_cx = [src_w / 2.0] * 2
        frame_times = [0.0, ctx.artifacts.get("duration", 1.0)]

    cx_arr = np.array(raw_cx, dtype=np.float64)

    # Dead-zone filter
    smoothed_dz = _dead_zone(cx_arr, dead_zone=crop_w * DEAD_ZONE_RATIO)

    # Savitzky-Golay
    win = min(SAVGOL_WINDOW, len(smoothed_dz) if len(smoothed_dz) % 2 == 1 else len(smoothed_dz) - 1)
    if win >= 5:
        smoothed = savgol_filter(smoothed_dz, window_length=win, polyorder=min(SAVGOL_POLY, win - 1))
    else:
        smoothed = smoothed_dz

    ctx.progress(STAGE, 80.0, "Clamping crop rects…")

    crop_plan: list[dict] = []
    for i, (fd, cx) in enumerate(zip(face_detections, smoothed)):
        x = int(cx - crop_w / 2)
        x = max(0, min(x, src_w - crop_w))
        y = max(0, (src_h - crop_h) // 2)  # vertically centred for now
        crop_plan.append({
            "frame": fd["frame"],
            "time": fd["time"],
            "x": x, "y": y,
            "w": crop_w, "h": crop_h,
        })

    ctx.artifacts["crop_plan"] = crop_plan
    ctx.artifacts["crop_w"] = crop_w
    ctx.artifacts["crop_h"] = crop_h

    ctx.progress(STAGE, 100.0, f"Crop path ready — {len(crop_plan)} keyframes, output {crop_w}×{crop_h}")


def _pick_target_cx(
    faces: list[dict],
    t: float,
    spk_lookup: dict[float, int | None],
    primary_tid: int | None,
    src_w: int,
) -> float:
    if not faces:
        return src_w / 2.0

    # Prefer active speaker at this time
    spk_tid = spk_lookup.get(round(t, 2))
    for f in faces:
        if f.get("track_id") == spk_tid or f.get("track_id") == primary_tid:
            return f["x"] + f["w"] / 2.0

    # Fallback: largest face
    largest = max(faces, key=lambda f: f["w"] * f["h"])
    return largest["x"] + largest["w"] / 2.0


def _dead_zone(arr: np.ndarray, dead_zone: float) -> np.ndarray:
    """Only move camera when subject exits dead-zone around current position."""
    out = np.copy(arr)
    current = arr[0]
    for i in range(1, len(arr)):
        if abs(arr[i] - current) > dead_zone:
            current = arr[i]
        out[i] = current
    return out
