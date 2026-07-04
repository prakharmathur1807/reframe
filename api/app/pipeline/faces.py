"""Face detection stage — MediaPipe BlazeFace with YOLOv11 fallback.

Samples frames at ~5 fps to build a per-frame face list. Each entry:
  {
    "frame": int,
    "time": float,
    "faces": [{"x": int, "y": int, "w": int, "h": int, "conf": float}]
  }

MediaPipe is tried first; YOLOv11 kicks in only if no faces are found in the
first sampled batch (handles heavy occlusion / side profiles).
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from .context import JobContext

STAGE = "faces"
SAMPLE_FPS = 5.0          # analyse this many frames per second
logger = logging.getLogger("reframe.faces")


def run(ctx: JobContext) -> None:
    ctx.progress(STAGE, 0.0, "Initialising face detector…")

    video_path = Path(ctx.require_artifact("video_path"))
    fps: float = ctx.artifacts.get("fps", 25.0)
    duration: float = ctx.artifacts.get("duration", 0.0)

    frame_interval = max(1, int(round(fps / SAMPLE_FPS)))
    detections: list[dict] = []

    # ── try MediaPipe ──────────────────────────────────────────────────────
    mp_ok = False
    try:
        import mediapipe as mp  # noqa: PLC0415
        detector = mp.solutions.face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.4
        )
        mp_ok = True
    except Exception:
        logger.warning("MediaPipe not available — will try YOLO")

    cap = cv2.VideoCapture(str(video_path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    frame_idx = 0
    yolo_fallback = False

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            t = frame_idx / fps
            faces = []

            if mp_ok and not yolo_fallback:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = detector.process(rgb)
                h, w = frame.shape[:2]
                if result.detections:
                    for det in result.detections:
                        bb = det.location_data.relative_bounding_box
                        faces.append({
                            "x": int(bb.xmin * w),
                            "y": int(bb.ymin * h),
                            "w": int(bb.width * w),
                            "h": int(bb.height * h),
                            "conf": round(det.score[0], 3),
                        })

            # Switch to YOLO if first 50 frames gave nothing
            if not faces and len(detections) > 50 and not any(
                d["faces"] for d in detections[-50:]
            ):
                yolo_fallback = True

            if yolo_fallback:
                faces = _yolo_detect(frame)

            detections.append({"frame": frame_idx, "time": round(t, 3), "faces": faces})

            pct = min(frame_idx / total_frames * 100, 99)
            if frame_idx % (frame_interval * 30) == 0:
                ctx.progress(STAGE, pct, f"Detecting faces… {t:.0f}s / {duration:.0f}s")

        frame_idx += 1

    cap.release()

    ctx.artifacts["face_detections"] = detections
    ctx.artifacts["used_yolo"] = yolo_fallback
    face_count = sum(len(d["faces"]) for d in detections)
    ctx.progress(STAGE, 100.0, f"Detected {face_count} face instances across {len(detections)} frames")


def _yolo_detect(frame: np.ndarray) -> list[dict]:
    try:
        from ultralytics import YOLO  # noqa: PLC0415
        model = _get_yolo()
        results = model(frame, classes=[0], verbose=False)  # class 0 = person
        faces = []
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            faces.append({
                "x": int(x1), "y": int(y1),
                "w": int(x2 - x1), "h": int(y2 - y1),
                "conf": round(float(box.conf[0]), 3),
            })
        return faces
    except Exception:
        return []


_yolo_model = None

def _get_yolo():
    global _yolo_model
    if _yolo_model is None:
        from ultralytics import YOLO  # noqa: PLC0415
        _yolo_model = YOLO("yolo11n.pt")
    return _yolo_model
