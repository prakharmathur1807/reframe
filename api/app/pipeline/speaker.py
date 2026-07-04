"""Speaker detection stage — find the active speaker per frame.

Strategy:
1. Compute short-time RMS energy of the audio track (window = ~0.1s).
2. For each tracked face, measure inter-frame vertical mouth motion as a
   proxy for lip activity (cheap, no landmark model needed).
3. Multiply energy × lip-motion score → speaking score per track per second.
4. At each timestamp the track with the highest score is the active speaker.

Output artifacts:
  active_speaker_timeline: [{time: float, track_id: int | None, score: float}]
  speaker_scores: {track_id: float}  (overall score, for ranking)
"""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from .context import JobContext

STAGE = "speaker"
ENERGY_WINDOW = 0.1      # seconds per RMS window
LIP_HEIGHT_RATIO = 0.4   # bottom 40% of face bbox = mouth region


def run(ctx: JobContext) -> None:
    ctx.progress(STAGE, 0.0, "Analysing audio energy…")

    pcm: np.ndarray = ctx.require_artifact("audio_pcm")
    sr: int = ctx.artifacts.get("sample_rate", 16000)
    tracks: dict = ctx.require_artifact("tracks")
    duration: float = ctx.artifacts.get("duration", len(pcm) / sr)

    # ── 1. Short-time RMS energy ───────────────────────────────────────────
    win = int(sr * ENERGY_WINDOW)
    n_windows = len(pcm) // win
    rms_times: list[float] = []
    rms_vals: list[float] = []
    for i in range(n_windows):
        chunk = pcm[i * win:(i + 1) * win]
        rms = math.sqrt(float(np.mean(chunk ** 2)) + 1e-9)
        rms_times.append(i * ENERGY_WINDOW)
        rms_vals.append(rms)

    rms_arr = np.array(rms_vals, dtype=np.float32)
    # normalise to 0–1
    if rms_arr.max() > 0:
        rms_arr /= rms_arr.max()

    ctx.progress(STAGE, 30.0, "Scoring lip activity per track…")

    # ── 2. Lip motion per track ────────────────────────────────────────────
    # For each track, build a time→lip_score map (Δ lower-face height)
    track_lip: dict[int, dict[float, float]] = defaultdict(dict)
    for tid_str, history in tracks.items():
        tid = int(tid_str)
        prev_mouth_h = None
        for entry in history:
            mouth_h = entry["h"] * LIP_HEIGHT_RATIO
            delta = abs(mouth_h - prev_mouth_h) if prev_mouth_h else 0.0
            # normalise by face height
            score = min(delta / (entry["h"] + 1e-9), 1.0)
            track_lip[tid][entry["time"]] = score
            prev_mouth_h = mouth_h

    # ── 3. Build per-second timeline ──────────────────────────────────────
    ctx.progress(STAGE, 60.0, "Building speaker timeline…")
    timeline: list[dict] = []
    speaker_totals: dict[int, float] = defaultdict(float)

    step = 0.1
    t = 0.0
    while t <= duration:
        # audio energy at this time
        ei = min(int(t / ENERGY_WINDOW), len(rms_arr) - 1)
        energy = float(rms_arr[ei])

        best_tid: int | None = None
        best_score = -1.0

        for tid_str, history in tracks.items():
            tid = int(tid_str)
            # closest lip score
            times = list(track_lip[tid].keys())
            if not times:
                continue
            closest = min(times, key=lambda x: abs(x - t))
            lip = track_lip[tid].get(closest, 0.0)
            score = energy * (0.3 + 0.7 * lip)
            if score > best_score:
                best_score = score
                best_tid = tid

        if best_tid is not None:
            speaker_totals[best_tid] += best_score

        timeline.append({"time": round(t, 2), "track_id": best_tid, "score": round(best_score, 4)})
        t = round(t + step, 3)

    ctx.artifacts["active_speaker_timeline"] = timeline
    ctx.artifacts["speaker_scores"] = {str(k): round(v, 2) for k, v in speaker_totals.items()}

    # primary speaker = highest cumulative score
    if speaker_totals:
        primary = max(speaker_totals, key=lambda k: speaker_totals[k])
        ctx.artifacts["primary_speaker_track"] = primary
    else:
        ctx.artifacts["primary_speaker_track"] = None

    ctx.progress(STAGE, 100.0, f"Primary speaker: track {ctx.artifacts['primary_speaker_track']}")
