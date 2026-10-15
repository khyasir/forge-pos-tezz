import type { UserRead } from "./types";

export interface Session {
  token: string;
  user: UserRead;
  companyId: string;
  branchId: string;
  branchName: string;
  terminalId: string;
  terminalName: string;
}

const SESSION_KEY = "tezz_session";
// Demo sandbox key, used only before PIN login (see app/login/page.tsx).
// api/app/seed.py seeds this exact fixed value (tz_test_tezzdemo...) on an
// empty database, so this works out of the box for local dev/demo; override
// via NEXT_PUBLIC_DEMO_API_KEY (build-time) if a deployment reseeds a
// different key.
export const DEMO_API_KEY = process.env.NEXT_PUBLIC_DEMO_API_KEY || "tz_test_tezzdemo0000000000000001";

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
  } catch {
    return null;
  }
}

export function saveSession(session: Session) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  window.dispatchEvent(new Event("tezz:session-changed"));
}

export function clearSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(SESSION_KEY);
  window.dispatchEvent(new Event("tezz:session-changed"));
}

export function getToken(): string | null {
  return getSession()?.token ?? null;
}
