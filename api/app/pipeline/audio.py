"""Audio extraction stage — pull a clean 16-kHz mono WAV from the source video.

faster-whisper expects 16 000 Hz mono PCM.  We also store the raw PCM as a
numpy array (float32, –1…1) so downstream stages (speaker energy, lip sync)
can analyse it without re-reading the file.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from .context import JobContext

STAGE = "audio"
SAMPLE_RATE = 16_000


def run(ctx: JobContext) -> None:
    ctx.progress(STAGE, 0.0, "Extracting audio…")

    video_path = Path(ctx.require_artifact("video_path"))
    out_wav = ctx.artifact_path("audio.wav")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",                    # drop video
        "-acodec", "pcm_s16le",
        "-ar", str(SAMPLE_RATE),
        "-ac", "1",               # mono
        str(out_wav),
    ]

    try:
        subprocess.run(
            cmd, capture_output=True, text=True, timeout=600, check=True
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"FFmpeg audio extraction failed: {exc.stderr[:300]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Audio extraction timed out") from exc

    ctx.progress(STAGE, 70.0, "Reading PCM samples…")

    # Load PCM as float32 numpy array (shape: [n_samples])
    raw = np.frombuffer(out_wav.read_bytes(), dtype=np.int16, offset=44)
    pcm = raw.astype(np.float32) / 32768.0

    ctx.artifacts["audio_path"] = str(out_wav)
    ctx.artifacts["audio_pcm"] = pcm          # numpy array, kept in memory
    ctx.artifacts["sample_rate"] = SAMPLE_RATE

    ctx.progress(STAGE, 100.0, f"Audio ready — {len(pcm) / SAMPLE_RATE:.1f}s @ {SAMPLE_RATE} Hz")
