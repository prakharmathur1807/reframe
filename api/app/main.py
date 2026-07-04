"""Reframe API — application entry point.

Run locally:
    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .core import cleanup
from .core.executor import pool
from .core.registry import registry
from .routes import health, jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("reframe")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    registry.bind_loop(asyncio.get_running_loop())
    cleanup.ensure_work_dir()
    cleanup.purge_orphans()
    pool.start()
    reaper_task = asyncio.create_task(cleanup.reaper(), name="reframe-reaper")
    logger.info("%s v%s ready (work dir: %s)", settings.app_name, settings.version, settings.work_dir)
    try:
        yield
    finally:
        reaper_task.cancel()
        try:
            await reaper_task
        except asyncio.CancelledError:
            pass
        pool.shutdown()
        cleanup.purge_all()
        logger.info("Shutdown complete — all temporary files deleted")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
