import { apiFetch, apiUrl } from "./client";
import { getAccessToken } from "./auth";

export type DocumentOut = {
  id: string;
  user_id: string;
  filename: string;
  mime_type: string;
  storage_url: string;
  type_detected?: string | null;
  date_of_issue?: string | null;
  date_of_expiry?: string | null;
  created_at: string;
};

export type RequiredDocument = {
  document_type: string;
  priority: string;
  required_for_crs: boolean;
  reason?: string;
  field_needed?: string;
};

export type DocumentsCrsStatusResponse = {
  uploaded_documents: DocumentOut[];
  uploaded_count: number;
  required_documents: RequiredDocument[];
  required_count: number;
  crs_requirements: {
    can_calculate: boolean;
    is_complete: boolean;
    available_fields: string[];
    missing_required: string[];
    missing_optional: string[];
    field_details: unknown[];
  };
  can_calculate_crs: boolean;
  is_complete: boolean;
  completion_percentage: number;
};

export type DeadlineItem = {
  document_id: string;
  filename: string;
  type_detected: string;
  date_of_expiry?: string | null;
  date_of_issue?: string | null;
  days_until_expiry?: number | null;
  expired: boolean;
};

export async function getDocumentsCrsStatus(): Promise<DocumentsCrsStatusResponse> {
  return apiFetch<DocumentsCrsStatusResponse>("/api/v1/documents/crs-status");
}

export async function getDocumentsDeadlines(): Promise<DeadlineItem[]> {
  return apiFetch<DeadlineItem[]>("/api/v1/documents/deadlines");
}

export async function uploadDocument(file: File): Promise<DocumentOut> {
  const form = new FormData();
  form.append("file", file);
  const url = apiUrl("/api/v1/documents");
  const token = getAccessToken();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(url, {
    method: "POST",
    headers,
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
  return res.json() as Promise<DocumentOut>;
}
