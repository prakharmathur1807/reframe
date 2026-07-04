"""Process pool for CPU-bound pipeline work.

FastAPI's event loop must stay responsive while Whisper, OpenCV and FFmpeg
grind through video, so every heavy stage runs in a separate process. The
pool is created lazily on startup and torn down on shutdown.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Callable, TypeVar

from ..config import settings

logger = logging.getLogger("reframe.executor")

T = TypeVar("T")


class ProcessPool:
    def __init__(self) -> None:
        self._pool: ProcessPoolExecutor | None = None

    def start(self) -> None:
        if self._pool is None:
            self._pool = ProcessPoolExecutor(max_workers=settings.max_workers)
            logger.info("Process pool started (max_workers=%d)", settings.max_workers)

    async def run(self, fn: Callable[..., T], *args: Any) -> T:
        """Run ``fn(*args)`` in a worker process and await the result.

        ``fn`` and its arguments must be picklable (module-level functions,
        plain data). Pipeline stages follow that contract.
        """
        if self._pool is None:
            raise RuntimeError("Process pool is not running")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._pool, fn, *args)

    def shutdown(self) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)
            self._pool = None
            logger.info("Process pool shut down")


pool = ProcessPool()
