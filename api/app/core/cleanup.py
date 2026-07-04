"""Temporary-file lifecycle.

Privacy guarantee: every artifact (source video, audio, transcript, rendered
clips) lives inside one directory per job under ``settings.work_dir`` and is
deleted when the job finishes its TTL, fails, or the server restarts.
Nothing is ever written outside that directory.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

from ..config import settings
from .registry import registry

logger = logging.getLogger("reframe.cleanup")


def ensure_work_dir() -> Path:
    settings.work_dir.mkdir(parents=True, exist_ok=True)
    return settings.work_dir


def create_job_dir(job_id: str) -> Path:
    path = settings.work_dir / job_id
    path.mkdir(parents=True, exist_ok=False)
    return path


def remove_dir(path: str | Path) -> None:
    target = Path(path)
    # Refuse to delete anything outside the sandboxed work directory.
    try:
        target.resolve().relative_to(settings.work_dir.resolve())
    except ValueError:
        logger.error("Refusing to delete path outside work dir: %s", target)
        return
    shutil.rmtree(target, ignore_errors=True)


def purge_orphans() -> int:
    """Delete work-dir entries that belong to no known job.

    Run at startup so a crash or restart never leaves user media on disk.
    On a fresh start the registry is empty, so this wipes everything.
    """
    ensure_work_dir()
    known = {job.id for job in registry.all_jobs()}
    removed = 0
    for entry in settings.work_dir.iterdir():
        if entry.name not in known:
            remove_dir(entry)
            removed += 1
    if removed:
        logger.info("Purged %d orphaned job director%s", removed, "y" if removed == 1 else "ies")
    return removed


def expire_job(job_id: str) -> None:
    job = registry.get(job_id)
    if job is None:
        return
    registry.mark_expired(job_id)
    remove_dir(job.temp_dir)
    registry.remove(job_id)


async def reaper() -> None:
    """Background task: delete expired jobs and their artifacts forever."""
    while True:
        try:
            expired = registry.collect_expired(
                ttl_seconds=settings.job_ttl_seconds,
                max_age_seconds=settings.job_max_age_seconds,
            )
            for job in expired:
                logger.info("Reaping job %s (status=%s)", job.id, job.status)
                expire_job(job.id)
        except Exception:  # noqa: BLE001 — the reaper must never die
            logger.exception("Reaper iteration failed")
        await asyncio.sleep(settings.reaper_interval_seconds)


def purge_all() -> None:
    """Delete every job directory (called on shutdown — stateless by design)."""
    for job in registry.all_jobs():
        remove_dir(job.temp_dir)
        registry.remove(job.id)
    if settings.work_dir.exists():
        for entry in settings.work_dir.iterdir():
            remove_dir(entry)
