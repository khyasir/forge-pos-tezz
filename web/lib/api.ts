// Thin fetch wrapper for the Tezz POS API. All paths are relative to
// NEXT_PUBLIC_API_BASE (default "/api"), which next.config.js rewrites to
// the FastAPI backend (see API_PROXY_TARGET there).
import { getToken } from "./auth";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  opts: RequestInit = {},
  tokenOverride?: string | null
): Promise<T> {
  const token = tokenOverride !== undefined ? tokenOverride : getToken();
  const headers: Record<string, string> = {
    ...(opts.body ? { "Content-Type": "application/json" } : {}),
    ...((opts.headers as Record<string, string>) || {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });

  if (!res.ok) {
    let detail = res.statusText || `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      /* non-JSON error body, keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

/** For endpoints that return raw HTML (receipt.html), not JSON. */
export async function getRawText(path: string, tokenOverride?: string | null): Promise<string> {
  const token = tokenOverride !== undefined ? tokenOverride : getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { headers });
  if (!res.ok) throw new ApiError(res.status, res.statusText || `HTTP ${res.status}`);
  return res.text();
}

export const api = {
  get: <T,>(path: string, token?: string | null) => request<T>(path, { method: "GET" }, token),
  post: <T,>(path: string, body?: unknown, token?: string | null) =>
    request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }, token),
  patch: <T,>(path: string, body?: unknown, token?: string | null) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }, token),
  put: <T,>(path: string, body?: unknown, token?: string | null) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }, token),
  del: <T,>(path: string, token?: string | null) => request<T>(path, { method: "DELETE" }, token),
  /** Fetches every page of a CRUD list endpoint (server caps limit at 200). */
  getAll: async <T,>(path: string, pageSize = 200): Promise<T[]> => {
    const out: T[] = [];
    const sep = path.includes("?") ? "&" : "?";
    for (let offset = 0; offset < 20000; offset += pageSize) {
      const page = await request<T[]>(`${path}${sep}limit=${pageSize}&offset=${offset}`, { method: "GET" });
      out.push(...page);
      if (page.length < pageSize) break;
    }
    return out;
  },
};
