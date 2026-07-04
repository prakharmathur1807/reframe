"""Full pipeline runner — chains all 11 stages.

This is the function submitted to the ProcessPool. It runs synchronously
inside a worker process and uses ctx.progress() for live updates.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .context import JobContext
from . import audio, captions, clip_detect, crop, faces, ingest, metadata, render, scenes, speaker, transcribe

logger = logging.getLogger("reframe.pipeline")


def run_full_pipeline(ctx: JobContext) -> dict:
    """Run all pipeline stages. Returns the result dict for registry.mark_ready()."""
    try:
        # Stage 1: Ingest (already done in upload/youtube route, re-run to populate ctx)
        ingest.run(ctx)

        # Stage 2: Audio extraction
        audio.run(ctx)

        # Stage 3: Transcription
        transcribe.run(ctx)

        # Stage 4: Scene detection
        scenes.run(ctx)

        # Stage 5: Face detection
        faces.run(ctx)

        # Stage 6: Tracking
        from . import tracking as tracking_mod  # noqa: PLC0415
        tracking_mod.run(ctx)

        # Stage 7: Speaker detection
        speaker.run(ctx)

        # Stage 8: Crop planning
        crop.run(ctx)

        # Stage 9: Clip detection + viral score
        clip_detect.run(ctx)

        # Stage 10: Captions
        captions.run(ctx)

        # Stage 11: Render
        render.run(ctx)

        # Stage 12: Metadata (post-render, no progress stage)
        metadata.run(ctx)

        # Trend matching
        transcript_text = ctx.artifacts.get("transcript_text", "")
        trend_matches: list[dict] = []
        try:
            from ..trends.providers import get_trends  # noqa: PLC0415
            from ..trends.matcher import match_transcript  # noqa: PLC0415
            trends = get_trends()
            matches = match_transcript(transcript_text, trends)
            trend_matches = [
                {
                    "keyword": m.keyword,
                    "category": m.category,
                    "trendScore": m.trend_score,
                    "relevancePct": m.relevance_pct,
                    "hashtags": m.hashtags,
                }
                for m in matches
            ]
        except Exception as e:
            logger.warning("Trend matching failed (non-fatal): %s", e)

        # Build result
        rendered: list[dict] = ctx.artifacts.get("rendered_clips", [])
        candidates: list[dict] = ctx.artifacts.get("clip_candidates", [])

        clips_out: list[dict] = []
        for rc in rendered:
            candidate = next((c for c in candidates if c["id"] == rc["clip_id"]), {})
            clips_out.append({
                "id": rc["clip_id"],
                "start": rc["start"],
                "end": rc["end"],
                "duration": round(rc["end"] - rc["start"], 2),
                "path": rc["path"],
                "viral_score": candidate.get("viral_score", 0),
                "title": candidate.get("title", ""),
                "hook": candidate.get("hook", ""),
                "explanation": candidate.get("explanation", ""),
                "wpm": candidate.get("wpm", 0),
                "metadata": candidate.get("metadata", {}),
            })

        return {
            "stage": "complete",
            "clips": clips_out,
            "clip_count": len(clips_out),
            "duration": ctx.duration_seconds,
            "width": ctx.width,
            "height": ctx.height,
            "fps": ctx.fps,
            "language": ctx.artifacts.get("language"),
            "word_count": len(ctx.artifacts.get("words", [])),
            "scene_count": len(ctx.artifacts.get("scenes", [])),
            "video_metadata": ctx.artifacts.get("video_metadata", {}),
            "trend_matches": trend_matches,
            "filename": ctx.original_filename,
        }

    except Exception as exc:
        logger.exception("Pipeline failed for job %s", ctx.job_id)
        raise
