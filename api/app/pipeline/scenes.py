"""Scene detection stage — find every hard cut using PySceneDetect.

Outputs a list of scene dicts:
  {"start": float, "end": float, "start_frame": int, "end_frame": int}
"""

from __future__ import annotations

from pathlib import Path

from .context import JobContext

STAGE = "scenes"


def run(ctx: JobContext) -> None:
    ctx.progress(STAGE, 0.0, "Detecting scene changes…")

    from scenedetect import open_video, SceneManager  # noqa: PLC0415
    from scenedetect.detectors import ContentDetector  # noqa: PLC0415

    video_path = Path(ctx.require_artifact("video_path"))

    video = open_video(str(video_path))
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=27.0))

    manager.detect_scenes(video, show_progress=False)
    raw = manager.get_scene_list()

    scenes: list[dict] = []
    for start_tc, end_tc in raw:
        scenes.append({
            "start": round(start_tc.get_seconds(), 3),
            "end": round(end_tc.get_seconds(), 3),
            "start_frame": start_tc.get_frames(),
            "end_frame": end_tc.get_frames(),
        })

    ctx.artifacts["scenes"] = scenes
    ctx.progress(STAGE, 100.0, f"Found {len(scenes)} scenes")
