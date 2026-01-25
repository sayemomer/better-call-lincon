import { apiFetch, apiUrl } from "./client";

export type SignupDocUploadResponse = {
  job_id: string;
  status: string;
};

export type SignupDocStatusResponse = {
  job_id: string;
  status: "queued" | "extracting" | "need_review" | "invalid_document" | "failed" | "completed";
  extracted: Record<string, unknown>;
  reason?: string | null;
  error?: string | null;
  needs_email_password: boolean;
  is_error: boolean;
  ocr_markdown?: string | null;
  ocr_extracted?: unknown;
};

const BASE = "/api/v1/auth";

export async function uploadSignupDoc(file: File): Promise<SignupDocUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const url = apiUrl(`${BASE}/signup-doc`);
  const res = await fetch(url, {
    method: "POST",
    body: form,
    credentials: "include",
  });
  if (!res.ok) {
    const text = await res.text();
    let detail: string;
    try {
      const j = JSON.parse(text) as { detail?: string };
      detail = typeof j.detail === "string" ? j.detail : text || res.statusText;
    } catch {
      detail = text || res.statusText;
    }
    throw new Error(detail);
  }
  return res.json() as Promise<SignupDocUploadResponse>;
}

export async function getSignupDocStatus(jobId: string): Promise<SignupDocStatusResponse> {
  return apiFetch<SignupDocStatusResponse>(`${BASE}/signup-doc/${jobId}`);
}

export const TERMINAL_STATUSES = [
  "need_review",
  "invalid_document",
  "failed",
  "completed",
] as const;

export function isTerminalStatus(s: string): s is (typeof TERMINAL_STATUSES)[number] {
  return (TERMINAL_STATUSES as readonly string[]).includes(s);
}

export type FinalizeSignupResponse = {
  access_token: string;
  token_type: string;
  user_id: string;
  message: string;
};

export async function finalizeSignup(
  jobId: string,
  email: string,
  password: string
): Promise<FinalizeSignupResponse> {
  const url = apiUrl(`${BASE}/signup-doc/finalize`);
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_id: jobId, email, password }),
    credentials: "include",
  });
  if (!res.ok) {
    const text = await res.text();
    let detail: string;
    try {
      const j = JSON.parse(text) as { detail?: string };
      detail = typeof j.detail === "string" ? j.detail : text || res.statusText;
    } catch {
      detail = text || res.statusText;
    }
    throw new Error(detail);
  }
  return res.json() as Promise<FinalizeSignupResponse>;
}
