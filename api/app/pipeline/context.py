"""JobContext — the single object that flows through the entire pipeline.

Every stage receives a context, writes its outputs into ``artifacts``, and
reports progress via ``progress()``. Nothing else is shared between stages.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..core.registry import JobSource


@dataclass
class JobContext:
    job_id: str
    source: JobSource
    temp_dir: Path

    # Filled by the ingest stage
    source_path: Path | None = None          # absolute path to the source video
    original_filename: str | None = None     # for display only
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None

    # Filled as pipeline progresses
    artifacts: dict[str, Any] = field(default_factory=dict)

    # Callback injected by the pipeline runner so stages can report progress
    # without importing the registry.
    _progress_cb: Callable[[str, float, str | None], None] | None = field(
        default=None, repr=False
    )

    def progress(self, stage: str, pct: float, message: str | None = None) -> None:
        if self._progress_cb is not None:
            self._progress_cb(stage, pct, message)

    def artifact_path(self, name: str) -> Path:
        """Return a path inside the job's temp dir for a named artifact."""
        return self.temp_dir / name

    def require_artifact(self, name: str) -> Any:
        if name not in self.artifacts:
            raise RuntimeError(f"Required artifact '{name}' is missing from context")
        return self.artifacts[name]
