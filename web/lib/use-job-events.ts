"use client";

/**
 * Subscribes to a job's SSE progress stream and exposes the latest snapshot.
 * Falls back to a one-off fetch on connection failure so terminal states are
 * never missed, and reconnects with backoff while the job is still running.
 */

import { useEffect, useRef, useState } from "react";

import { getJob, jobEventsUrl } from "./api";
import { TERMINAL_STATUSES, type JobSnapshot } from "./types";

export type JobStreamState = "connecting" | "live" | "done" | "error";

export function useJobEvents(jobId: string | null) {
  const [snapshot, setSnapshot] = useState<JobSnapshot | null>(null);
  const [state, setState] = useState<JobStreamState>("connecting");
  const retryRef = useRef(0);

  useEffect(() => {
    if (!jobId) return;

    let source: EventSource | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let disposed = false;

    const handleSnapshot = (event: MessageEvent) => {
      const parsed = JSON.parse(event.data) as JobSnapshot;
      setSnapshot(parsed);
    };

    const connect = () => {
      if (disposed) return;
      setState("connecting");
      source = new EventSource(jobEventsUrl(jobId));

      source.addEventListener("open", () => {
        retryRef.current = 0;
        setState("live");
      });
      source.addEventListener("snapshot", handleSnapshot);
      source.addEventListener("done", (event) => {
        handleSnapshot(event as MessageEvent);
        setState("done");
        source?.close();
      });
      source.addEventListener("error", () => {
        source?.close();
        if (disposed) return;
        // Check whether the job finished while we were disconnected.
        getJob(jobId)
          .then((job) => {
            setSnapshot(job);
            if (TERMINAL_STATUSES.has(job.status)) {
              setState("done");
              return;
            }
            scheduleRetry();
          })
          .catch(() => {
            scheduleRetry();
          });
      });
    };

    const scheduleRetry = () => {
      if (disposed) return;
      retryRef.current += 1;
      if (retryRef.current > 5) {
        setState("error");
        return;
      }
      const delay = Math.min(1000 * 2 ** retryRef.current, 15000);
      retryTimer = setTimeout(connect, delay);
    };

    connect();

    return () => {
      disposed = true;
      if (retryTimer) clearTimeout(retryTimer);
      source?.close();
    };
  }, [jobId]);

  return { snapshot, state };
}
