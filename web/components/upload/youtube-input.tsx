"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Youtube, ArrowRight, AlertCircle, Loader2 } from "lucide-react";

import { submitYoutubeUrl, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const YT_RE =
  /^https?:\/\/(www\.)?(youtube\.com\/watch\?.*v=[\w-]{11}|youtu\.be\/[\w-]{11})/;

type Phase =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "error"; message: string };

export function YoutubeInput() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });

  const isValid = YT_RE.test(url.trim());
  const isSubmitting = phase.kind === "submitting";

  const submit = async () => {
    if (!isValid || isSubmitting) return;
    setPhase({ kind: "submitting" });
    try {
      const { jobId } = await submitYoutubeUrl(url.trim());
      router.push(`/processing/${jobId}`);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : "Failed to submit URL — check the API is running";
      setPhase({ kind: "error", message: msg });
    }
  };

  return (
    <div className="w-full space-y-3">
      {/* disclaimer */}
      <div className="rounded-lg border border-guide/25 bg-guide/5 p-3 text-sm text-dim">
        <span className="font-medium text-guide">⚠ Your responsibility:</span>{" "}
        Only submit YouTube URLs for videos you own or have explicit permission
        to download and process. The downloaded file is deleted immediately
        after processing.
      </div>

      {/* input row */}
      <div className="flex gap-2">
        <div className={cn(
          "flex flex-1 items-center gap-2 rounded-lg border bg-panel px-3 transition-colors",
          url && !isValid ? "border-rec/60" : "border-line focus-within:border-rec/50",
        )}>
          <Youtube className="h-4 w-4 shrink-0 text-dim" />
          <input
            type="url"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              if (phase.kind === "error") setPhase({ kind: "idle" });
            }}
            onKeyDown={(e) => e.key === "Enter" && isValid && submit()}
            placeholder="https://youtube.com/watch?v=…"
            className="flex-1 bg-transparent py-3 text-sm text-chalk placeholder:text-dim/60 focus:outline-none"
            disabled={isSubmitting}
            spellCheck={false}
          />
          {url && (
            <span className={cn(
              "shrink-0 font-mono text-xs",
              isValid ? "text-guide" : "text-rec/70",
            )}>
              {isValid ? "valid" : "invalid"}
            </span>
          )}
        </div>

        <Button
          onClick={submit}
          disabled={!isValid || isSubmitting}
          size="default"
          className="shrink-0 gap-2"
        >
          {isSubmitting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <ArrowRight className="h-4 w-4" />
          )}
          {isSubmitting ? "Starting…" : "Process"}
        </Button>
      </div>

      {/* error */}
      {phase.kind === "error" && (
        <div className="flex items-start gap-2 rounded-lg border border-rec/30 bg-rec/5 p-3 text-sm text-rec">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{phase.message}</span>
        </div>
      )}

      <p className="font-mono text-xs text-dim">
        youtube.com/watch?v=… and youtu.be/… links accepted
      </p>
    </div>
  );
}
