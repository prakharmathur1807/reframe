"""Chunked video upload endpoint + full pipeline trigger."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from ..config import settings
from ..core.cleanup import create_job_dir, remove_dir
from ..core.executor import pool
from ..core.registry import JobSource, registry
from ..pipeline.context import JobContext
from ..pipeline.runner import run_full_pipeline

logger = logging.getLogger("reframe.upload")
router = APIRouter(tags=["ingest"])

CHUNK = 1024 * 1024
ALLOWED_MIME_PREFIXES = ("video/", "application/octet-stream")


def _validate_mime(content_type: str | None) -> None:
    if content_type and not any(content_type.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        raise HTTPException(status_code=415, detail=f"Unsupported media type '{content_type}'.")


@router.post("/upload")
async def upload_video(request: Request, file: UploadFile) -> JSONResponse:
    _validate_mime(file.content_type)

    original_name = file.filename or "upload"
    suffix = Path(original_name).suffix.lower() or ".mp4"

    job = registry.create(JobSource.UPLOAD, "/tmp")
    job_dir = create_job_dir(job.id)
    registry.update(job.id, temp_dir=str(job_dir))

    dest = job_dir / f"source{suffix}"
    total_bytes = 0
    content_length = request.headers.get("content-length")
    expected = int(content_length) if content_length else None

    registry.set_progress(job.id, "ingest", 0.0, "Receiving file…")

    try:
        with dest.open("wb") as fh:
            while True:
                chunk = await file.read(CHUNK)
                if not chunk:
                    break
                fh.write(chunk)
                total_bytes += len(chunk)
                if expected and expected > 0:
                    pct = min(total_bytes / expected * 10.0, 10.0)
                    registry.set_progress(job.id, "ingest", pct,
                                          f"Receiving… {total_bytes // (1024*1024)} MB")
                if total_bytes > settings.max_upload_bytes:
                    raise HTTPException(status_code=413, detail="File too large")
    except HTTPException:
        registry.mark_failed(job.id, "Upload interrupted")
        remove_dir(job_dir)
        raise
    except Exception as exc:
        registry.mark_failed(job.id, f"Upload failed: {exc}")
        remove_dir(job_dir)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    registry.set_progress(job.id, "ingest", 12.0, "File received — starting pipeline…")

    ctx = JobContext(
        job_id=job.id,
        source=JobSource.UPLOAD,
        temp_dir=job_dir,
        source_path=dest,
        original_filename=original_name,
        _progress_cb=lambda stage, pct, msg: registry.set_progress(job.id, stage, pct, msg),
    )
    asyncio.create_task(_run(ctx))
    return JSONResponse({"jobId": job.id}, status_code=202)


async def _run(ctx: JobContext) -> None:
    job_id = ctx.job_id
    try:
        result = await pool.run(run_full_pipeline, ctx)
        registry.mark_ready(job_id, result)
    except Exception as exc:
        registry.mark_failed(job_id, str(exc))
