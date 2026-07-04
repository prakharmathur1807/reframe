"""Job inspection and live progress via Server-Sent Events."""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..config import settings
from ..core.registry import TERMINAL_STATUSES, JobStatus, registry

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.snapshot()


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


@router.get("/{job_id}/events")
async def job_events(job_id: str) -> StreamingResponse:
    """Stream job snapshots as SSE until the job reaches a terminal state.

    Events:
      - ``snapshot``  — full job state (sent on connect and on every change)
      - ``done``      — final state; the stream closes after this
      - ``ping``      — heartbeat to keep proxies from closing the connection
    """
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    async def stream() -> AsyncIterator[str]:
        queue = registry.subscribe(job_id)
        try:
            current = registry.get(job_id)
            if current is None:
                return
            snapshot = current.snapshot()
            if JobStatus(snapshot["status"]) in TERMINAL_STATUSES:
                yield _sse("done", snapshot)
                return
            yield _sse("snapshot", snapshot)

            while True:
                try:
                    snapshot = await asyncio.wait_for(
                        queue.get(), timeout=settings.sse_heartbeat_seconds
                    )
                except asyncio.TimeoutError:
                    yield _sse("ping", {"t": asyncio.get_running_loop().time()})
                    continue

                # Coalesce bursts: only the newest snapshot matters.
                while not queue.empty():
                    snapshot = queue.get_nowait()

                if JobStatus(snapshot["status"]) in TERMINAL_STATUSES:
                    yield _sse("done", snapshot)
                    return
                yield _sse("snapshot", snapshot)
        finally:
            registry.unsubscribe(job_id, queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
