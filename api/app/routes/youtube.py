"""YouTube URL intake endpoint.

POST /api/youtube   body: {url: string}

Downloads only the best single-file ≤1080p stream for the given URL using
yt-dlp, validates it with ffprobe, then hands it to the ingest stage.
The downloaded file is **automatically deleted** as part of normal job cleanup
— it is never stored permanently.

Users are responsible for ensuring they have the right to download and process
the video. The endpoint refuses private/age-gated videos that require auth.
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from ..core.cleanup import create_job_dir, remove_dir
from ..core.executor import pool
from ..core.registry import JobSource, registry
from ..pipeline.context import JobContext
from ..pipeline.ingest import run as ingest_run

logger = logging.getLogger("reframe.youtube")
router = APIRouter(tags=["ingest"])

# Matches standard youtube.com/watch?v= and youtu.be/ URLs only.
_YT_RE = re.compile(
    r"^https?://(www\.)?(youtube\.com/watch\?.*v=[\w-]{11}|youtu\.be/[\w-]{11})"
)


class YoutubeRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not _YT_RE.match(v):
            raise ValueError(
                "Only standard YouTube watch URLs (youtube.com/watch?v=… or "
                "youtu.be/…) are accepted."
            )
        return v


@router.post("/youtube")
async def ingest_youtube(body: YoutubeRequest) -> dict:
    job_dir = Path("/tmp")
    job = registry.create(JobSource.YOUTUBE, str(job_dir))
    job_dir = create_job_dir(job.id)
    registry.update(job.id, temp_dir=str(job_dir))
    registry.set_progress(job.id, "ingest", 0.0, "Starting download…")

    asyncio.create_task(_download_and_ingest(job.id, body.url, job_dir))
    return {"jobId": job.id}


async def _download_and_ingest(job_id: str, url: str, job_dir: Path) -> None:
    try:
        dest = await pool.run(_download, job_id, url, job_dir)
    except ValueError as exc:
        registry.mark_failed(job_id, str(exc))
        return
    except Exception as exc:
        logger.exception("Download failed for job %s", job_id)
        registry.mark_failed(job_id, f"Download error: {exc}")
        return

    registry.set_progress(job_id, "ingest", 50.0, "Download complete — probing…")

    ctx = JobContext(
        job_id=job_id,
        source=JobSource.YOUTUBE,
        temp_dir=job_dir,
        source_path=dest,
        original_filename=dest.name,
        _progress_cb=lambda stage, pct, msg: registry.set_progress(job_id, stage, pct, msg),
    )

    try:
        await pool.run(ingest_run, ctx)
        registry.mark_ready(
            job_id,
            {
                "stage": "ingest_complete",
                "duration": ctx.duration_seconds,
                "width": ctx.width,
                "height": ctx.height,
                "fps": ctx.fps,
                "filename": ctx.original_filename,
                "source": "youtube",
                "sourceUrl": url,
            },
        )
    except ValueError as exc:
        registry.mark_failed(job_id, str(exc))
    except Exception as exc:
        logger.exception("Ingest failed for job %s", job_id)
        registry.mark_failed(job_id, f"Processing error: {exc}")


def _download(job_id: str, url: str, job_dir: Path) -> Path:
    """Blocking download — runs in the process pool."""
    try:
        import yt_dlp  # noqa: PLC0415
    except ImportError as exc:
        raise ValueError(
            "yt-dlp is not installed. Run: pip install yt-dlp"
        ) from exc

    dest_template = str(job_dir / "source.%(ext)s")

    def _progress_hook(d: dict) -> None:
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                pct = downloaded / total * 45.0
                registry.set_progress(
                    job_id,
                    "ingest",
                    pct,
                    f"Downloading… {downloaded // (1024*1024)} / "
                    f"{total // (1024*1024)} MB",
                )

    ydl_opts = {
        # Best single-file stream ≤ 1080p — avoids separate audio merge which
        # requires ffmpeg muxing at download time.
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]"
                  "/best[height<=1080][ext=mp4]/best[height<=1080]/best",
        "outtmpl": dest_template,
        "noplaylist": True,
        "noprogress": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_progress_hook],
        # Never use cookies — the endpoint is for publicly accessible videos.
        "cookiefile": None,
        "username": None,
        "password": None,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise ValueError("yt-dlp could not retrieve video info")
    except yt_dlp.utils.DownloadError as exc:
        msg = str(exc)
        if "Private video" in msg or "Sign in" in msg:
            raise ValueError(
                "This video is private or requires sign-in. "
                "Only publicly accessible videos can be processed."
            ) from exc
        if "age" in msg.lower():
            raise ValueError(
                "This video is age-restricted and cannot be downloaded without auth."
            ) from exc
        raise ValueError(f"Download failed: {msg[:200]}") from exc

    # Find the downloaded file (yt-dlp resolves the extension).
    candidates = sorted(job_dir.glob("source.*"))
    if not candidates:
        raise ValueError("Download appeared to succeed but no output file was found")

    downloaded = candidates[0]
    return downloaded
