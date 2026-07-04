"use client";

import { useCallback, useEffect, useState } from "react";

import { getHealth } from "@/lib/api";
import type { HealthResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";

type Status =
  | { kind: "loading" }
  | { kind: "online"; health: HealthResponse }
  | { kind: "offline"; detail: string };

export function ApiStatus() {
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  const check = useCallback(async () => {
    setStatus({ kind: "loading" });
    try {
      const health = await getHealth();
      setStatus({ kind: "online", health });
    } catch (error) {
      setStatus({
        kind: "offline",
        detail:
          error instanceof Error ? error.message : "Could not reach the API",
      });
    }
  }, []);

  useEffect(() => {
    void check();
    const interval = setInterval(() => void check(), 30_000);
    return () => clearInterval(interval);
  }, [check]);

  return (
    <div className="rounded-lg border border-line bg-panel p-5">
      <div className="flex items-center justify-between gap-4">
        <h3 className="font-display text-base font-semibold">
          Processing engine
        </h3>
        <StatusPill status={status} />
      </div>

      {status.kind === "online" && (
        <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-4">
          <Field label="Service" value={status.health.service} />
          <Field label="Version" value={status.health.version} mono />
          <Field
            label="FFmpeg"
            value={status.health.ffmpegAvailable ? "detected" : "missing"}
            warn={!status.health.ffmpegAvailable}
          />
          <Field
            label="Active jobs"
            value={String(status.health.activeJobs)}
            mono
          />
        </dl>
      )}

      {status.kind === "offline" && (
        <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-dim">
          <p>
            The API at{" "}
            <code className="font-mono text-chalk">
              {process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}
            </code>{" "}
            didn&apos;t respond ({status.detail}). Start it with{" "}
            <code className="font-mono text-chalk">
              uvicorn app.main:app --port 8000
            </code>
            , then retry.
          </p>
          <Button variant="secondary" size="sm" onClick={() => void check()}>
            Retry
          </Button>
        </div>
      )}
    </div>
  );
}

function StatusPill({ status }: { status: Status }) {
  const styles = {
    loading: "border-line text-dim",
    online: "border-guide/40 text-guide",
    offline: "border-rec/40 text-rec",
  } as const;
  const label = {
    loading: "checking…",
    online: "online",
    offline: "offline",
  } as const;
  return (
    <span
      role="status"
      className={`rounded-full border px-2.5 py-0.5 font-mono text-xs ${styles[status.kind]}`}
    >
      {label[status.kind]}
    </span>
  );
}

function Field({
  label,
  value,
  mono,
  warn,
}: {
  label: string;
  value: string;
  mono?: boolean;
  warn?: boolean;
}) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-dim">{label}</dt>
      <dd
        className={`mt-0.5 ${mono ? "font-mono" : ""} ${warn ? "text-rec" : "text-chalk"}`}
      >
        {value}
      </dd>
    </div>
  );
}
