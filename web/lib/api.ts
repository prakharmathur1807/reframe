/** Thin, typed client for the Reframe API. */

import type { HealthResponse, JobSnapshot } from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // non-JSON error body — keep statusText
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export function getJob(jobId: string): Promise<JobSnapshot> {
  return request<JobSnapshot>(`/api/jobs/${jobId}`);
}

/** URL for the job's Server-Sent Events progress stream. */
export function jobEventsUrl(jobId: string): string {
  return `${API_URL}/api/jobs/${jobId}/events`;
}

export { ApiError };
