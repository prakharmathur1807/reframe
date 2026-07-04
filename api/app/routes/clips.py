"""Clips route — list candidates and download rendered clips."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..core.registry import registry

router = APIRouter(prefix="/clips", tags=["clips"])


@router.get("/{job_id}")
async def list_clips(job_id: str) -> dict:
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("ready",):
        raise HTTPException(status_code=400, detail=f"Job not ready (status={job.status})")

    result = job.result or {}
    return {
        "jobId": job_id,
        "clips": result.get("clips", []),
        "videoMetadata": result.get("video_metadata", {}),
        "trendMatches": result.get("trend_matches", []),
    }


@router.get("/{job_id}/{clip_id}/download")
async def download_clip(job_id: str, clip_id: str) -> FileResponse:
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    result = job.result or {}
    clips = result.get("clips", [])
    clip = next((c for c in clips if c["id"] == clip_id), None)
    if clip is None:
        raise HTTPException(status_code=404, detail="Clip not found")

    path = Path(clip.get("path", ""))
    if not path.exists():
        raise HTTPException(status_code=410, detail="Clip file has been deleted")

    return FileResponse(
        path=str(path),
        media_type="video/mp4",
        filename=f"reframe_clip_{clip_id}.mp4",
    )
