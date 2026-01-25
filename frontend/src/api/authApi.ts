import { apiUrl } from "./client";
import { setAccessToken, clearAccessToken } from "./auth";

const BASE = "/api/v1/auth";

export type SignInResponse = {
  access_token: string;
  token_type: string;
};

async function handleError(res: Response): Promise<never> {
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

export async function signIn(email: string, password: string): Promise<SignInResponse> {
  const url = apiUrl(`${BASE}/signin`);
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
    credentials: "include",
  });
  if (!res.ok) throw await handleError(res);
  const data = (await res.json()) as SignInResponse;
  setAccessToken(data.access_token);
  return data;
}

export async function signOut(): Promise<void> {
  const url = apiUrl(`${BASE}/signout`);
  try {
    const res = await fetch(url, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) throw await handleError(res);
  } finally {
    clearAccessToken();
  }
}
