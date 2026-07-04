"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Loader2, XCircle } from "lucide-react";

import { getJob, ApiError } from "@/lib/api";
import { ClipCard } from "@/components/preview/clip-card";
import { Button } from "@/components/ui/button";

interface Clip {
  id: string;
  start: number;
  end: number;
  duration: number;
  viral_score: number;
  title: string;
  hook: string;
  explanation: string;
  wpm: number;
  metadata?: Record<string, unknown>;
}

interface JobResult {
  clips: Clip[];
  clip_count: number;
  duration: number;
  language: string;
  word_count: number;
  scene_count: number;
  filename: string;
  video_metadata: {
    hashtags?: string[];
    seo_keywords?: string[];
  };
}

export default function PreviewPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = typeof params.jobId === "string" ? params.jobId : "";
  const [result, setResult] = useState<JobResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!jobId) return;
    getJob(jobId)
      .then((job) => {
        if (job.status === "ready" && job.result) {
          setResult(job.result as unknown as JobResult);
        } else if (job.status === "processing" || job.status === "queued") {
          router.replace(`/processing/${jobId}`);
        } else {
          setError(job.error ?? "Job not available");
        }
      })
      .catch((e: unknown) => setError(e instanceof ApiError ? e.message : "Failed to load job"))
      .finally(() => setLoading(false));
  }, [jobId, router]);

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-rec" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <XCircle className="mx-auto h-12 w-12 text-rec" />
        <h1 className="mt-4 font-display text-xl font-semibold">Something went wrong</h1>
        <p className="mt-2 text-sm text-dim">{error}</p>
        <Button className="mt-6" onClick={() => router.push("/upload")}>Try again</Button>
      </div>
    );
  }

  if (!result) return null;

  const avgScore = result.clips.length
    ? Math.round(result.clips.reduce((a, c) => a + c.viral_score, 0) / result.clips.length)
    : 0;

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
      <Link href="/" className="mb-8 inline-flex items-center gap-1.5 font-mono text-xs text-dim hover:text-chalk">
        <ArrowLeft className="h-3.5 w-3.5" />
        Home
      </Link>

      {/* summary bar */}
      <div className="mb-8 rounded-lg border border-line bg-panel p-5">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-dim">Processing complete</p>
        <h1 className="mt-2 font-display text-2xl font-semibold tracking-tight">
          {result.clip_count} clip{result.clip_count !== 1 ? "s" : ""} ready
        </h1>
        <dl className="mt-4 grid grid-cols-2 gap-x-8 gap-y-2 text-sm sm:grid-cols-4">
          <Field label="Source" value={result.filename?.slice(0, 20) ?? "—"} />
          <Field label="Duration" value={`${result.duration?.toFixed(0) ?? "—"}s`} />
          <Field label="Language" value={result.language?.toUpperCase() ?? "—"} />
          <Field label="Avg score" value={`${avgScore}/100`} />
        </dl>
      </div>

      {/* clips */}
      {result.clips.length === 0 ? (
        <div className="rounded-lg border border-line bg-panel p-8 text-center">
          <p className="text-dim">No clips were generated. Try a longer video with clear speech.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {result.clips.map((clip, i) => (
            <ClipCard key={clip.id} clip={clip} jobId={jobId} index={i} />
          ))}
        </div>
      )}

      {/* global hashtags */}
      {result.video_metadata?.hashtags && result.video_metadata.hashtags.length > 0 && (
        <div className="mt-8 rounded-lg border border-line bg-panel p-4">
          <p className="mb-2 text-xs text-dim">Suggested hashtags for this video</p>
          <div className="flex flex-wrap gap-1.5">
            {result.video_metadata.hashtags.map((h) => (
              <span key={h} className="rounded border border-line px-2 py-0.5 font-mono text-[11px] text-dim">
                {h}
              </span>
            ))}
          </div>
        </div>
      )}

      <p className="mt-8 text-center font-mono text-xs text-dim">
        Files auto-delete after 1 hour · job {jobId.slice(0, 8)}…
      </p>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-dim">{label}</dt>
      <dd className="mt-0.5 font-mono text-sm text-chalk">{value}</dd>
    </div>
  );
}
