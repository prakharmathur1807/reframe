"""Tracking stage — assign stable IDs to faces across frames.

Uses a lightweight IoU-based tracker (ByteTrack logic) so we can follow the
same person across cuts without requiring the full ByteTrack C++ library.
Each tracked detection gets a ``track_id`` field added in-place.

Output artifact ``tracks``:
  {track_id: [{"frame": int, "time": float, "x":…, "y":…, "w":…, "h":…}]}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple

from .context import JobContext

STAGE = "tracking"
IOU_THRESHOLD = 0.35
MAX_MISS_FRAMES = 15   # frames a track may be absent before being closed


class _Box(NamedTuple):
    x: int
    y: int
    w: int
    h: int

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    def iou(self, other: "_Box") -> float:
        ix1 = max(self.x, other.x)
        iy1 = max(self.y, other.y)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if inter == 0:
            return 0.0
        union = self.w * self.h + other.w * other.h - inter
        return inter / union if union else 0.0


@dataclass
class _Track:
    id: int
    box: _Box
    missed: int = 0
    history: list[dict] = field(default_factory=list)


def run(ctx: JobContext) -> None:
    ctx.progress(STAGE, 0.0, "Assigning track IDs…")

    detections: list[dict] = ctx.require_artifact("face_detections")
    tracks: dict[int, _Track] = {}
    next_id = 0
    closed: dict[int, list[dict]] = {}

    for i, frame_det in enumerate(detections):
        f_idx = frame_det["frame"]
        t = frame_det["time"]
        faces = frame_det.get("faces", [])

        det_boxes = [_Box(f["x"], f["y"], f["w"], f["h"]) for f in faces]
        matched_track_ids: set[int] = set()
        matched_det_ids: set[int] = set()

        # Match detections to existing tracks by IoU
        for tid, track in list(tracks.items()):
            best_iou = IOU_THRESHOLD
            best_det = -1
            for di, dbox in enumerate(det_boxes):
                if di in matched_det_ids:
                    continue
                iou = track.box.iou(dbox)
                if iou > best_iou:
                    best_iou = iou
                    best_det = di
            if best_det >= 0:
                dbox = det_boxes[best_det]
                track.box = dbox
                track.missed = 0
                entry = {"frame": f_idx, "time": t,
                         "x": dbox.x, "y": dbox.y, "w": dbox.w, "h": dbox.h,
                         "conf": faces[best_det]["conf"]}
                track.history.append(entry)
                faces[best_det]["track_id"] = tid
                matched_track_ids.add(tid)
                matched_det_ids.add(best_det)

        # Increment missed count for unmatched tracks
        for tid in list(tracks.keys()):
            if tid not in matched_track_ids:
                tracks[tid].missed += 1
                if tracks[tid].missed > MAX_MISS_FRAMES:
                    closed[tid] = tracks.pop(tid).history

        # Create new tracks for unmatched detections
        for di, dbox in enumerate(det_boxes):
            if di not in matched_det_ids:
                entry = {"frame": f_idx, "time": t,
                         "x": dbox.x, "y": dbox.y, "w": dbox.w, "h": dbox.h,
                         "conf": faces[di]["conf"]}
                t_new = _Track(id=next_id, box=dbox, history=[entry])
                tracks[next_id] = t_new
                faces[di]["track_id"] = next_id
                next_id += 1

        if i % 100 == 0:
            ctx.progress(STAGE, i / len(detections) * 100, f"Tracking… frame {f_idx}")

    # Merge open tracks into closed
    for tid, track in tracks.items():
        closed[tid] = track.history

    ctx.artifacts["tracks"] = closed
    ctx.progress(STAGE, 100.0, f"Tracking complete — {len(closed)} unique subjects")
