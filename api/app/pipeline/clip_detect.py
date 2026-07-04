"""Clip detection and Viral Score stage.

Analyses the transcript + audio energy + scene changes to propose
the best 20–90 second clips, each with a 0–100 Viral Score and explanation.

Scoring dimensions:
  hook_strength   — strong opening sentence (question / bold statement)
  speech_energy   — words-per-minute variance (high energy = dynamic)
  emotional_words — lexicon match (positive + negative emotions)
  scene_activity  — scene cuts within the clip
  pacing          — WPM (too slow or too fast is penalised)
  clip_length     — sweet spot 30–60s

Output artifact ``clip_candidates``:
  [{"id": str, "start": float, "end": float, "viral_score": int,
    "title": str, "hook": str, "explanation": str, "wpm": float}]
"""

from __future__ import annotations

import re
import uuid
from collections import defaultdict

import numpy as np

from .context import JobContext

STAGE = "clips"

MIN_CLIP = 20.0
MAX_CLIP = 90.0
SWEET_SPOT = (30.0, 60.0)

_HOOK_WORDS = {
    "?", "secret", "never", "always", "worst", "best", "mistake",
    "truth", "actually", "nobody", "everybody", "shocking", "honest",
    "promise", "wrong", "right", "stop", "start", "why", "how",
}
_EMOTION_POS = {
    "amazing", "incredible", "love", "great", "awesome", "fantastic",
    "perfect", "beautiful", "brilliant", "excellent", "happy", "joy",
}
_EMOTION_NEG = {
    "hate", "terrible", "awful", "disaster", "fail", "mistake",
    "wrong", "bad", "horrible", "problem", "struggle", "hard",
}


def run(ctx: JobContext, max_clips: int = 5) -> None:
    ctx.progress(STAGE, 0.0, "Analysing transcript for clip candidates…")

    segments: list[dict] = ctx.require_artifact("segments")
    words: list[dict] = ctx.require_artifact("words")
    scenes: list[dict] = ctx.artifacts.get("scenes", [])
    pcm: np.ndarray = ctx.artifacts.get("audio_pcm", np.zeros(1))
    sr: int = ctx.artifacts.get("sample_rate", 16000)
    duration: float = ctx.artifacts.get("duration", 0.0)

    if not segments:
        ctx.artifacts["clip_candidates"] = []
        ctx.progress(STAGE, 100.0, "No transcript segments — skipping clip detection")
        return

    # ── Build candidate windows (sliding over sentence boundaries) ────────
    candidates: list[dict] = []
    n = len(segments)

    for i in range(n):
        for j in range(i + 1, n + 1):
            start = segments[i]["start"]
            end = segments[j - 1]["end"]
            length = end - start
            if length < MIN_CLIP:
                continue
            if length > MAX_CLIP:
                break

            window_segs = segments[i:j]
            window_words = [w for w in words if start <= w["start"] <= end]

            score, explanation = _score(
                window_segs, window_words, start, end, scenes, pcm, sr
            )
            candidates.append({
                "id": uuid.uuid4().hex[:8],
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(length, 2),
                "viral_score": score,
                "explanation": explanation,
                "text": " ".join(s["text"] for s in window_segs),
                "wpm": round(len(window_words) / (length / 60), 1) if length else 0,
            })

        if len(candidates) > 500:
            break

    ctx.progress(STAGE, 60.0, f"Scored {len(candidates)} windows — selecting top {max_clips}…")

    # De-duplicate by overlap, keep highest score
    selected = _select_non_overlapping(candidates, max_clips)

    # Add title / hook
    for clip in selected:
        clip["title"] = _make_title(clip["text"])
        clip["hook"] = _make_hook(clip["text"])

    ctx.artifacts["clip_candidates"] = selected
    ctx.progress(STAGE, 100.0, f"Selected {len(selected)} clips")


def _score(
    segs: list[dict],
    words: list[dict],
    start: float,
    end: float,
    scenes: list[dict],
    pcm: np.ndarray,
    sr: int,
) -> tuple[int, str]:
    length = end - start
    reasons: list[str] = []
    total = 0.0

    # 1. Hook strength (first segment)
    first_text = segs[0]["text"].lower() if segs else ""
    hook_score = sum(1 for w in _HOOK_WORDS if w in first_text) / len(_HOOK_WORDS) * 25
    if hook_score > 5:
        reasons.append("strong hook")
    total += hook_score

    # 2. Emotional words
    all_text = " ".join(s["text"].lower() for s in segs)
    pos = sum(1 for w in _EMOTION_POS if w in all_text)
    neg = sum(1 for w in _EMOTION_NEG if w in all_text)
    emo = min((pos + neg) / 3 * 20, 20)
    if emo > 8:
        reasons.append("emotional content")
    total += emo

    # 3. Speech energy (RMS variance in window)
    s_i = int(start * sr)
    e_i = int(end * sr)
    chunk = pcm[s_i:e_i] if len(pcm) > e_i else pcm[s_i:]
    if len(chunk) > 0:
        rms_var = float(np.std(chunk)) * 100
        energy_score = min(rms_var * 20, 20)
        if energy_score > 10:
            reasons.append("high audio energy")
    else:
        energy_score = 10.0
    total += energy_score

    # 4. Scene cuts
    scene_cuts = sum(1 for sc in scenes if start <= sc["start"] <= end)
    scene_score = min(scene_cuts * 3, 15)
    if scene_score > 6:
        reasons.append("scene variety")
    total += scene_score

    # 5. Clip length sweet spot
    if SWEET_SPOT[0] <= length <= SWEET_SPOT[1]:
        length_score = 20.0
        reasons.append("ideal length")
    elif length < SWEET_SPOT[0]:
        length_score = (length / SWEET_SPOT[0]) * 20
    else:
        length_score = max(0, 20 - (length - SWEET_SPOT[1]) / 3)
    total += length_score

    score = max(0, min(100, int(total)))
    explanation = ", ".join(reasons) if reasons else "solid content"
    return score, explanation


def _select_non_overlapping(candidates: list[dict], n: int) -> list[dict]:
    sorted_c = sorted(candidates, key=lambda c: -c["viral_score"])
    selected: list[dict] = []
    for c in sorted_c:
        if len(selected) >= n:
            break
        overlap = any(
            not (c["end"] <= s["start"] or c["start"] >= s["end"])
            for s in selected
        )
        if not overlap:
            selected.append(c)
    return sorted(selected, key=lambda c: c["start"])


def _make_title(text: str) -> str:
    sentences = re.split(r"[.!?]", text)
    first = next((s.strip() for s in sentences if len(s.strip()) > 15), text[:60])
    words = first.split()[:8]
    title = " ".join(words).strip().rstrip(",;:")
    return title[:60]


def _make_hook(text: str) -> str:
    words = text.split()[:20]
    return " ".join(words) + ("…" if len(text.split()) > 20 else "")
