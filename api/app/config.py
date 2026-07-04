"""Application configuration.

All values can be overridden with environment variables prefixed with
``REFRAME_`` (e.g. ``REFRAME_WORK_DIR=/data/tmp``) or an ``api/.env`` file.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="REFRAME_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Reframe API"
    version: str = "0.2.0"

    # --- Storage (temporary only — the service is stateless) -------------
    work_dir: Path = Path("/tmp/reframe")

    # --- Job lifecycle ----------------------------------------------------
    # How long a finished/failed job (and its artifacts) may live before the
    # reaper deletes it. Keeps downloads available briefly, nothing more.
    job_ttl_seconds: int = 60 * 60
    # Hard ceiling for any job regardless of state (guards against jobs that
    # never reach a terminal state, e.g. a crashed worker).
    job_max_age_seconds: int = 6 * 60 * 60
    reaper_interval_seconds: int = 60

    # --- Input limits -----------------------------------------------------
    max_upload_bytes: int = 8 * 1024**3  # 8 GiB ≈ 2 h of high-bitrate video
    max_video_duration_seconds: int = 2 * 60 * 60

    # --- Compute ----------------------------------------------------------
    max_workers: int = 2  # CPU-heavy pipeline processes

    # --- HTTP -------------------------------------------------------------
    cors_origins: list[str] = ["http://localhost:3000"]
    sse_heartbeat_seconds: float = 15.0


settings = Settings()
