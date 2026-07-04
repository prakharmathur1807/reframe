"""In-memory job registry.

The application is deliberately stateless: no database, no persistence.
Every job lives here for the duration of processing plus a short TTL so the
user can download results, then the reaper removes it together with its
temporary directory.

Mutations are guarded by a lock and every change is fanned out to
per-subscriber ``asyncio.Queue`` instances, which the SSE endpoint drains.
Publishing is done via ``loop.call_soon_threadsafe`` so worker threads and
executor callbacks may safely report progress.
"""

from __future__ import annotations

import asyncio
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"


TERMINAL_STATUSES = {JobStatus.READY, JobStatus.FAILED, JobStatus.EXPIRED}


class JobSource(StrEnum):
    UPLOAD = "upload"
    YOUTUBE = "youtube"


#: Canonical pipeline stage identifiers, in execution order. The frontend
#: renders these; workers report progress against them.
PIPELINE_STAGES: tuple[str, ...] = (
    "ingest",
    "audio",
    "transcribe",
    "scenes",
    "faces",
    "tracking",
    "speaker",
    "crop",
    "clips",
    "captions",
    "render",
)


@dataclass
class Job:
    id: str
    source: JobSource
    temp_dir: str
    status: JobStatus = JobStatus.QUEUED
    stage: str | None = None
    progress: float = 0.0  # overall 0–100
    message: str | None = None
    error: str | None = None
    result: dict[str, Any] | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    def snapshot(self) -> dict[str, Any]:
        """JSON-safe view of the job, shared with the frontend."""
        return {
            "id": self.id,
            "source": self.source.value,
            "status": self.status.value,
            "stage": self.stage,
            "progress": round(self.progress, 1),
            "message": self.message,
            "error": self.error,
            "result": self.result,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "finishedAt": self.finished_at,
        }


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    # -- lifecycle ---------------------------------------------------------

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Attach the running event loop (called once at startup)."""
        self._loop = loop

    # -- CRUD ----------------------------------------------------------------

    def create(self, source: JobSource, temp_dir: str) -> Job:
        job = Job(id=uuid.uuid4().hex, source=source, temp_dir=temp_dir)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def all_jobs(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())

    def active_count(self) -> int:
        with self._lock:
            return sum(
                1 for j in self._jobs.values() if j.status not in TERMINAL_STATUSES
            )

    def remove(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.pop(job_id, None)
            self._subscribers.pop(job_id, None)
        return job

    # -- mutation + fan-out ----------------------------------------------------

    def update(self, job_id: str, **fields: Any) -> Job | None:
        """Apply field updates and notify subscribers. Thread-safe."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            for key, value in fields.items():
                if not hasattr(job, key):
                    raise AttributeError(f"Job has no field {key!r}")
                setattr(job, key, value)
            job.updated_at = time.time()
            if job.status in TERMINAL_STATUSES and job.finished_at is None:
                job.finished_at = job.updated_at
            snapshot = job.snapshot()
            queues = tuple(self._subscribers.get(job_id, ()))
        self._publish(queues, snapshot)
        return job

    def set_progress(
        self, job_id: str, stage: str, progress: float, message: str | None = None
    ) -> None:
        self.update(
            job_id,
            status=JobStatus.PROCESSING,
            stage=stage,
            progress=max(0.0, min(100.0, progress)),
            message=message,
        )

    def mark_ready(self, job_id: str, result: dict[str, Any]) -> None:
        self.update(
            job_id,
            status=JobStatus.READY,
            progress=100.0,
            message="Processing complete",
            result=result,
        )

    def mark_failed(self, job_id: str, error: str) -> None:
        self.update(job_id, status=JobStatus.FAILED, error=error, message=None)

    def mark_expired(self, job_id: str) -> None:
        self.update(job_id, status=JobStatus.EXPIRED, result=None)

    # -- expiry ----------------------------------------------------------------

    def collect_expired(self, ttl_seconds: int, max_age_seconds: int) -> list[Job]:
        now = time.time()
        expired: list[Job] = []
        with self._lock:
            for job in self._jobs.values():
                too_old = now - job.created_at > max_age_seconds
                done_and_stale = (
                    job.finished_at is not None
                    and now - job.finished_at > ttl_seconds
                )
                if too_old or done_and_stale:
                    expired.append(job)
        return expired

    # -- subscriptions -----------------------------------------------------------

    def subscribe(self, job_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
        with self._lock:
            self._subscribers.setdefault(job_id, set()).add(queue)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        with self._lock:
            subscribers = self._subscribers.get(job_id)
            if subscribers is not None:
                subscribers.discard(queue)
                if not subscribers:
                    self._subscribers.pop(job_id, None)

    def _publish(
        self,
        queues: tuple[asyncio.Queue[dict[str, Any]], ...],
        snapshot: dict[str, Any],
    ) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            return

        def _put() -> None:
            for queue in queues:
                try:
                    queue.put_nowait(snapshot)
                except asyncio.QueueFull:
                    # A slow consumer only loses intermediate snapshots; the
                    # SSE handler always re-reads the latest state on drain.
                    pass

        loop.call_soon_threadsafe(_put)


registry = JobRegistry()
