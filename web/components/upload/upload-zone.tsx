"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileVideo, AlertCircle } from "lucide-react";

import { uploadVideo, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const ACCEPTED = [".mp4", ".mov", ".mkv", ".avi", ".webm"];
const ACCEPT_ATTR = "video/mp4,video/quicktime,video/x-matroska,video/x-msvideo,video/webm,video/*";
const MAX_GB = 8;
const MAX_BYTES = MAX_GB * 1024 ** 3;

type Phase =
  | { kind: "idle" }
  | { kind: "dragging" }
  | { kind: "uploading"; file: File; pct: number }
  | { kind: "error"; message: string };

export function UploadZone() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });

  const start = useCallback((file: File) => {
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ACCEPTED.includes(ext)) {
      setPhase({ kind: "error", message: `Unsupported format (${ext}). Use: ${ACCEPTED.join(", ")}` });
      return;
    }
    if (file.size > MAX_BYTES) {
      setPhase({ kind: "error", message: `File is too large — max ${MAX_GB} GB` });
      return;
    }

    setPhase({ kind: "uploading", file, pct: 0 });

    uploadVideo(file, (pct) =>
      setPhase((prev) =>
        prev.kind === "uploading" ? { ...prev, pct } : prev,
      ),
    )
      .then(({ jobId }) => router.push(`/processing/${jobId}`))
      .catch((err: unknown) => {
        const msg =
          err instanceof ApiError
            ? err.message
            : "Upload failed — check the API is running";
        setPhase({ kind: "error", message: msg });
      });
  }, [router]);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file) start(file);
      else setPhase({ kind: "idle" });
    },
    [start],
  );

  const isUploading = phase.kind === "uploading";
  const isDragging = phase.kind === "dragging";

  return (
    <div className="w-full">
      <div
        role="button"
        tabIndex={isUploading ? -1 : 0}
        aria-label="Upload video — click or drag and drop"
        onClick={() => !isUploading && inputRef.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && !isUploading && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setPhase({ kind: "dragging" }); }}
        onDragLeave={() => setPhase({ kind: "idle" })}
        onDrop={onDrop}
        className={cn(
          "relative flex min-h-[280px] cursor-pointer flex-col items-center justify-center gap-4 rounded-lg border-2 border-dashed transition-colors",
          isDragging && "border-rec bg-rec/5",
          isUploading && "cursor-default border-line",
          !isDragging && !isUploading && "border-line hover:border-rec/50 hover:bg-raised/40",
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT_ATTR}
          className="sr-only"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) start(f); }}
          disabled={isUploading}
        />

        {phase.kind === "uploading" ? (
          <UploadProgress file={phase.file} pct={phase.pct} />
        ) : (
          <IdleState dragging={isDragging} />
        )}
      </div>

      {phase.kind === "error" && (
        <div className="mt-3 flex items-start gap-2 rounded-lg border border-rec/30 bg-rec/5 p-3 text-sm text-rec">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{phase.message}</span>
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto shrink-0 text-rec hover:bg-rec/10"
            onClick={() => setPhase({ kind: "idle" })}
          >
            Retry
          </Button>
        </div>
      )}
    </div>
  );
}

function IdleState({ dragging }: { dragging: boolean }) {
  return (
    <>
      <div className={cn(
        "rounded-full border-2 border-dashed p-5 transition-colors",
        dragging ? "border-rec text-rec" : "border-line text-dim",
      )}>
        {dragging ? (
          <FileVideo className="h-8 w-8" />
        ) : (
          <Upload className="h-8 w-8" />
        )}
      </div>
      <div className="text-center">
        <p className="font-medium text-chalk">
          {dragging ? "Drop to upload" : "Drag your video here"}
        </p>
        <p className="mt-1 text-sm text-dim">or click to browse</p>
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        {["MP4", "MOV", "MKV", "AVI", "WebM"].map((fmt) => (
          <span
            key={fmt}
            className="rounded border border-line px-2 py-0.5 font-mono text-[11px] text-dim"
          >
            {fmt}
          </span>
        ))}
      </div>
      <p className="font-mono text-xs text-dim">max {MAX_GB} GB · up to 2 hours</p>
    </>
  );
}

function UploadProgress({ file, pct }: { file: File; pct: number }) {
  const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
  return (
    <div className="w-full max-w-sm space-y-4 px-6">
      <div className="flex items-center gap-3">
        <FileVideo className="h-5 w-5 shrink-0 text-rec" />
        <span className="truncate text-sm text-chalk">{file.name}</span>
        <span className="ml-auto shrink-0 font-mono text-xs text-dim">{sizeMB} MB</span>
      </div>
      <div>
        <div className="mb-1.5 flex justify-between font-mono text-xs text-dim">
          <span>Uploading…</span>
          <span>{Math.round(pct)}%</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-raised">
          <div
            className="h-full rounded-full bg-rec transition-all duration-300"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
      <p className="text-center font-mono text-xs text-dim">
        processing begins once upload completes
      </p>
    </div>
  );
}
