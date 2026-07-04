"""Foundation tests: registry semantics, cleanup safety, HTTP surface, SSE."""

from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.core import cleanup
from app.core.registry import JobSource, JobStatus, registry
from app.main import app


@pytest.fixture
async def client():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.mark.anyio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["ffmpegAvailable"], bool)
    assert body["activeJobs"] == 0


@pytest.mark.anyio
async def test_job_lifecycle_and_snapshot(client: AsyncClient) -> None:
    job_dir = cleanup.create_job_dir("t-lifecycle")
    job = registry.create(JobSource.UPLOAD, str(job_dir))
    try:
        response = await client.get(f"/api/jobs/{job.id}")
        assert response.status_code == 200
        assert response.json()["status"] == JobStatus.QUEUED.value

        registry.set_progress(job.id, "transcribe", 42.0, "Transcribing audio")
        snapshot = (await client.get(f"/api/jobs/{job.id}")).json()
        assert snapshot["status"] == "processing"
        assert snapshot["stage"] == "transcribe"
        assert snapshot["progress"] == 42.0

        registry.mark_ready(job.id, {"clips": []})
        snapshot = (await client.get(f"/api/jobs/{job.id}")).json()
        assert snapshot["status"] == "ready"
        assert snapshot["finishedAt"] is not None
    finally:
        cleanup.expire_job(job.id)
    assert not job_dir.exists()


@pytest.mark.anyio
async def test_unknown_job_is_404(client: AsyncClient) -> None:
    assert (await client.get("/api/jobs/nope")).status_code == 404
    assert (await client.get("/api/jobs/nope/events")).status_code == 404


@pytest.mark.anyio
async def test_sse_streams_progress_until_done(client: AsyncClient) -> None:
    job_dir = cleanup.create_job_dir("t-sse")
    job = registry.create(JobSource.YOUTUBE, str(job_dir))

    async def drive() -> None:
        await asyncio.sleep(0.05)
        registry.set_progress(job.id, "faces", 55.0)
        await asyncio.sleep(0.05)
        registry.mark_ready(job.id, {"clips": [{"id": "c1"}]})

    driver = asyncio.create_task(drive())
    events: list[str] = []
    try:
        async with client.stream("GET", f"/api/jobs/{job.id}/events") as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if line.startswith("event: "):
                    events.append(line.removeprefix("event: "))
                if events and events[-1] == "done" and line == "":
                    break
    finally:
        await driver
        cleanup.expire_job(job.id)

    assert events[0] == "snapshot"
    assert events[-1] == "done"


def test_remove_dir_refuses_paths_outside_work_dir(tmp_path) -> None:
    victim = tmp_path / "precious"
    victim.mkdir()
    cleanup.remove_dir(victim)
    assert victim.exists()  # untouched — safety rail held
