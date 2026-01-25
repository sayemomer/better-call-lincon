import { getAccessToken, setAccessToken, clearAccessToken } from "./auth";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const AUTH_REFRESH_PATH = "/api/v1/auth/refresh";

export function apiUrl(path: string): string {
  const base = API_BASE.replace(/\/$/, "");
  const p = path.startsWith("/") ? path : `/${path}`;
  return base ? `${base}${p}` : p;
}

function parseErrorDetail(text: string): string {
  try {
    const j = JSON.parse(text) as { detail?: string };
    return typeof j.detail === "string" ? j.detail : text || "Request failed";
  } catch {
    return text || "Request failed";
  }
}

async function refreshToken(): Promise<void> {
  const res = await fetch(apiUrl(AUTH_REFRESH_PATH), {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) {
    clearAccessToken();
    throw new Error(parseErrorDetail(await res.text()));
  }
  const data = (await res.json()) as { access_token: string };
  setAccessToken(data.access_token);
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
  skipRefresh?: boolean
): Promise<T> {
  const url = apiUrl(path);
  const headers = new Headers(init?.headers);
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(url, {
    ...init,
    headers,
    credentials: "include",
  });

  if (res.status === 401 && !skipRefresh && !path.includes("/auth/refresh")) {
    const text = await res.text();
    const detail = parseErrorDetail(text);
    if (detail.toLowerCase().includes("invalid access token")) {
      try {
        await refreshToken();
        return apiFetch<T>(path, init, true);
      } catch (e) {
        throw e;
      }
    }
    throw new Error(detail);
  }

  if (!res.ok) {
    throw new Error(parseErrorDetail(await res.text()));
  }
  const contentType = res.headers.get("content-type");
  if (contentType?.includes("application/json")) return res.json() as Promise<T>;
  return res.text() as unknown as T;
}
