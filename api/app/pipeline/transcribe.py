"""Transcription stage — faster-whisper with word-level timestamps.

Produces a flat list of word dicts:
  {"word": str, "start": float, "end": float, "probability": float}

and a list of segment dicts (sentence-level) for caption generation.
Model is loaded once per process and cached in a module-level variable so
repeated calls within the same worker reuse the loaded weights.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .context import JobContext

STAGE = "transcribe"
logger = logging.getLogger("reframe.transcribe")

# Module-level model cache (per worker process)
_model: Any = None
_model_size: str = ""


def _get_model(model_size: str = "base") -> Any:
    global _model, _model_size
    if _model is None or _model_size != model_size:
        from faster_whisper import WhisperModel  # noqa: PLC0415
        logger.info("Loading Whisper model '%s'…", model_size)
        _model = WhisperModel(model_size, device="cpu", compute_type="int8")
        _model_size = model_size
    return _model


def run(ctx: JobContext, model_size: str = "base") -> None:
    ctx.progress(STAGE, 0.0, f"Loading Whisper ({model_size})…")

    audio_path = Path(ctx.require_artifact("audio_path"))
    model = _get_model(model_size)

    ctx.progress(STAGE, 15.0, "Transcribing — this takes a moment…")

    segments_raw, info = model.transcribe(
        str(audio_path),
        word_timestamps=True,
        vad_filter=True,
        language=None,   # auto-detect
    )

    words: list[dict] = []
    segments: list[dict] = []

    total = info.duration or 1.0
    processed = 0.0

    for seg in segments_raw:
        seg_words: list[dict] = []
        for w in (seg.words or []):
            words.append({
                "word": w.word,
                "start": round(w.start, 3),
                "end": round(w.end, 3),
                "probability": round(w.probability, 3),
            })
            seg_words.append(words[-1])

        segments.append({
            "id": seg.id,
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip(),
            "words": seg_words,
        })

        processed = seg.end
        pct = 15.0 + min(processed / total, 1.0) * 80.0
        ctx.progress(STAGE, pct, f"Transcribed {processed:.0f}s / {total:.0f}s")

    ctx.artifacts["words"] = words
    ctx.artifacts["segments"] = segments
    ctx.artifacts["language"] = info.language
    ctx.artifacts["transcript_text"] = " ".join(w["word"] for w in words).strip()

    ctx.progress(
        STAGE, 100.0,
        f"Transcript ready — {len(words)} words, lang={info.language}"
    )
