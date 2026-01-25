import { apiFetch } from "./client";

export type CRSComputeOverrides = {
  age?: number | null;
  marital_status?: string | null;
  spouse_accompanying?: boolean | null;
  education_level?: string | null;
  education_level_detail?: string | null;
  canadian_education?: boolean | null;
  language_scores?: Record<string, unknown> | null;
  canadian_work_years?: number | null;
  foreign_work_years?: number | null;
  certificate_of_qualification?: boolean | null;
  provincial_nomination?: boolean | null;
  sibling_in_canada?: boolean | null;
};

export type CRSComputeResponse = {
  total: number;
  core_human_capital: number;
  spouse_factors: number;
  skill_transferability: number;
  additional_points: number;
  breakdown: Record<string, unknown>;
  missing_or_defaulted: string[];
  disclaimer: string;
};

/**
 * Compute Express Entry CRS score from the user's profile.
 * Uses profile data from the backend; optional overrides supplement for this request only.
 */
export async function computeCrs(
  overrides?: CRSComputeOverrides | null
): Promise<CRSComputeResponse> {
  return apiFetch<CRSComputeResponse>("/api/v1/crs/compute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(overrides ?? {}),
  });
}
