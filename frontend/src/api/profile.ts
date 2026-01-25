import { apiFetch } from "./client";

export type ProfileOut = {
  id: string;
  user_id: string;
  status?: string | null;
  surname?: string | null;
  given_name?: string | null;
  dob?: string | null;
  citizenship?: string | null;
  sex?: string | null;
  place_of_birth?: string | null;
  passport_number?: string | null;
  country_code?: string | null;
  personal_number?: string | null;
  previous_passport_no?: string | null;
  date_of_issue?: string | null;
  date_of_expiry?: string | null;
  fathers_name?: string | null;
  mothers_name?: string | null;
  marital_status?: string | null;
  permanent_address?: string | null;
  travel_history?: unknown[] | null;
  province?: string | null;
  city?: string | null;
  arrival_date?: string | null;
  education_json?: Record<string, unknown> | null;
  language_json?: Record<string, unknown> | null;
  work_json?: Record<string, unknown> | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type ProfileValidationResult = {
  is_valid: boolean;
  missing_fields: string[];
  incomplete_sections: string[];
  recommendations: string[];
};

export async function getProfile(): Promise<ProfileOut> {
  return apiFetch<ProfileOut>("/api/v1/profile");
}

export async function getProfileValidate(): Promise<ProfileValidationResult> {
  return apiFetch<ProfileValidationResult>("/api/v1/profile/validate");
}
