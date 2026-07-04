/** Thin, typed client for the Reframe API. */

import type { HealthResponse, JobSnapshot } from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
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
      // non-JSON error body
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

export function jobEventsUrl(jobId: string): string {
  return `${API_URL}/api/jobs/${jobId}/events`;
}

/** Upload a video file with XHR for real upload progress reporting. */
export function uploadVideo(
  file: File,
  onProgress: (pct: number) => void,
): Promise<{ jobId: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    form.append("file", file);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) onProgress((e.loaded / e.total) * 100);
    });

    xhr.addEventListener("load", () => {
      if (xhr.status === 202) {
        try {
          resolve(JSON.parse(xhr.responseText) as { jobId: string });
        } catch {
          reject(new ApiError(xhr.status, "Invalid response from server"));
        }
      } else {
        let detail = xhr.statusText;
        try {
          const body = JSON.parse(xhr.responseText) as { detail?: string };
          if (body.detail) detail = body.detail;
        } catch {
          // keep statusText
        }
        reject(new ApiError(xhr.status, detail));
      }
    });

    xhr.addEventListener("error", () =>
      reject(new ApiError(0, "Network error — is the API running?")),
    );
    xhr.addEventListener("abort", () =>
      reject(new ApiError(0, "Upload cancelled")),
    );

    xhr.open("POST", `${API_URL}/api/upload`);
    xhr.send(form);
  });
}

/** Submit an authorized YouTube URL for processing. */
export async function submitYoutubeUrl(
  url: string,
): Promise<{ jobId: string }> {
  return request<{ jobId: string }>("/api/youtube", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
}
