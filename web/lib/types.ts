/** Types shared with the FastAPI backend (mirrors Job.snapshot()). */

export type JobStatus =
  | "queued"
  | "processing"
  | "ready"
  | "failed"
  | "expired";

export type JobSource = "upload" | "youtube";

export interface JobSnapshot {
  id: string;
  source: JobSource;
  status: JobStatus;
  stage: string | null;
  progress: number;
  message: string | null;
  error: string | null;
  result: Record<string, unknown> | null;
  createdAt: number;
  updatedAt: number;
  finishedAt: number | null;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  ffmpegAvailable: boolean;
  activeJobs: number;
  maxUploadBytes: number;
  maxVideoDurationSeconds: number;
}

/** Pipeline stages in execution order — must match PIPELINE_STAGES in the API. */
export const PIPELINE_STAGES = [
  { id: "ingest", label: "Ingest", detail: "Probe and normalize the source video" },
  { id: "audio", label: "Extract audio", detail: "FFmpeg pulls a clean mono track" },
  { id: "transcribe", label: "Transcribe", detail: "faster-whisper with word timestamps" },
  { id: "scenes", label: "Detect scenes", detail: "PySceneDetect finds every cut" },
  { id: "faces", label: "Detect faces", detail: "MediaPipe, YOLOv11 as fallback" },
  { id: "tracking", label: "Track subjects", detail: "ByteTrack keeps identities stable" },
  { id: "speaker", label: "Find the speaker", detail: "Audio energy meets lip motion" },
  { id: "crop", label: "Plan the 9:16 crop", detail: "Smoothed virtual-camera path" },
  { id: "clips", label: "Score clip candidates", detail: "Hooks, energy, and Viral Score" },
  { id: "captions", label: "Build captions", detail: "Karaoke-timed .ass subtitles" },
  { id: "render", label: "Render", detail: "H.264, 1080 × 1920, burned-in captions" },
] as const;

export const TERMINAL_STATUSES: ReadonlySet<JobStatus> = new Set([
  "ready",
  "failed",
  "expired",
]);
