"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { CheckCircle2, Circle, Loader2, XCircle, AlertCircle } from "lucide-react";

import { useJobEvents } from "@/lib/use-job-events";
import { PIPELINE_STAGES, TERMINAL_STATUSES } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export default function ProcessingPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = typeof params.jobId === "string" ? params.jobId : null;
  const { snapshot } = useJobEvents(jobId);

  // Redirect to preview once ready (Module 9 adds the preview page).
  useEffect(() => {
    if (snapshot?.status === "ready") {
      router.push(`/preview/${jobId}`);
    }
  }, [snapshot, router]);

  if (!jobId) {
    return <ErrorState message="Invalid job ID" />;
  }

  if (!snapshot) {
    return <LoadingState />;
  }

  if (snapshot.status === "failed") {
    return <ErrorState message={snapshot.error ?? "Processing failed"} jobId={jobId} />;
  }

  if (snapshot.status === "expired") {
    return <ErrorState message="This job has expired. Please upload your video again." />;
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-dim">
            {snapshot.source === "youtube" ? "YouTube · Processing" : "Upload · Processing"}
          </p>
          <h1 className="mt-2 font-display text-2xl font-semibold tracking-tight">
            {snapshot.status === "ready" ? "Done!" : "Processing your video…"}
          </h1>
        </div>
        <StatusBadge status={snapshot.status} />
      </div>

      {/* Overall progress bar */}
      <div className="mb-8">
        <div className="mb-2 flex justify-between font-mono text-xs text-dim">
          <span>{snapshot.message ?? "Working…"}</span>
          <span>{Math.round(snapshot.progress)}%</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-raised">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              snapshot.status === "ready" ? "bg-guide" : "bg-rec",
            )}
            style={{ width: `${snapshot.progress}%` }}
          />
        </div>
      </div>

      {/* Stage list */}
      <ol className="space-y-1">
        {PIPELINE_STAGES.map((stage) => {
          const state = getStageState(stage.id, snapshot.stage, snapshot.status, snapshot.progress);
          return (
            <li
              key={stage.id}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors",
                state === "active" && "bg-raised",
              )}
            >
              <StageIcon state={state} />
              <div className="min-w-0 flex-1">
                <span className={cn(
                  "text-sm font-medium",
                  state === "done" ? "text-dim" : "text-chalk",
                  state === "pending" && "text-dim/60",
                )}>
                  {stage.label}
                </span>
                {state === "active" && snapshot.message && (
                  <p className="mt-0.5 truncate font-mono text-xs text-dim">
                    {snapshot.message}
                  </p>
                )}
              </div>
              {state === "active" && (
                <span className="shrink-0 font-mono text-xs text-rec">
                  {Math.round(snapshot.progress)}%
                </span>
              )}
            </li>
          );
        })}
      </ol>

      {snapshot.status === "ready" && snapshot.result && (
        <ReadyCard result={snapshot.result} />
      )}

      <p className="mt-8 text-center font-mono text-xs text-dim">
        job · {jobId.slice(0, 8)}… · files deleted on completion
      </p>
    </div>
  );
}

// ---- helpers ---------------------------------------------------------------

type StageState = "done" | "active" | "pending";

function getStageState(
  stageId: string,
  currentStage: string | null,
  status: string,
  progress: number,
): StageState {
  const stages = PIPELINE_STAGES.map((s) => s.id);
  const currentIdx = currentStage ? stages.indexOf(currentStage as typeof stages[number]) : -1;
  const thisIdx = stages.indexOf(stageId as typeof stages[number]);

  if (status === "ready") return "done";
  if (thisIdx < currentIdx) return "done";
  if (thisIdx === currentIdx) return "active";
  return "pending";
}

function StageIcon({ state }: { state: StageState }) {
  if (state === "done")
    return <CheckCircle2 className="h-4 w-4 shrink-0 text-guide" />;
  if (state === "active")
    return <Loader2 className="h-4 w-4 shrink-0 animate-spin text-rec" />;
  return <Circle className="h-4 w-4 shrink-0 text-line" />;
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    queued: "border-line text-dim",
    processing: "border-rec/40 text-rec",
    ready: "border-guide/40 text-guide",
    failed: "border-rec text-rec",
  };
  return (
    <span className={cn("rounded-full border px-2.5 py-0.5 font-mono text-xs", map[status] ?? "border-line text-dim")}>
      {status}
    </span>
  );
}

function LoadingState() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-rec" />
    </div>
  );
}

function ErrorState({ message, jobId }: { message: string; jobId?: string }) {
  return (
    <div className="mx-auto max-w-lg px-4 py-16 text-center sm:px-6">
      <XCircle className="mx-auto h-12 w-12 text-rec" />
      <h1 className="mt-4 font-display text-xl font-semibold">Processing failed</h1>
      <p className="mt-2 text-sm text-dim">{message}</p>
      {jobId && (
        <p className="mt-1 font-mono text-xs text-dim">job: {jobId.slice(0, 8)}…</p>
      )}
      <Button className="mt-6" onClick={() => window.location.href = "/upload"}>
        Try again
      </Button>
    </div>
  );
}

function ReadyCard({ result }: { result: Record<string, unknown> }) {
  return (
    <div className="mt-8 rounded-lg border border-guide/30 bg-guide/5 p-5">
      <div className="flex items-center gap-2 text-guide">
        <CheckCircle2 className="h-5 w-5" />
        <span className="font-medium">Ingest complete</span>
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
        {result.duration != null && (
          <Field label="Duration" value={`${Number(result.duration).toFixed(1)}s`} />
        )}
        {result.width != null && result.height != null && (
          <Field label="Resolution" value={`${result.width}×${result.height}`} />
        )}
        {result.fps != null && (
          <Field label="FPS" value={String(result.fps)} />
        )}
        {result.filename != null && (
          <Field label="File" value={String(result.filename).slice(0, 20)} />
        )}
      </dl>
      <p className="mt-3 text-sm text-dim">
        AI pipeline stages (transcription, face detection, crop planning) will chain automatically from Module 4 onward.
      </p>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-dim">{label}</dt>
      <dd className="mt-0.5 font-mono text-chalk">{value}</dd>
    </div>
  );
}
