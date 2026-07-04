"""Service health and capability report."""

from __future__ import annotations

import shutil

from fastapi import APIRouter
from pydantic import BaseModel

from ..config import settings
from ..core.registry import registry

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    ffmpegAvailable: bool
    activeJobs: int
    maxUploadBytes: int
    maxVideoDurationSeconds: int


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.version,
        ffmpegAvailable=shutil.which("ffmpeg") is not None,
        activeJobs=registry.active_count(),
        maxUploadBytes=settings.max_upload_bytes,
        maxVideoDurationSeconds=settings.max_video_duration_seconds,
    )
