"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Logo from "@/components/Logo";
import LangToggle from "@/components/LangToggle";
import { useLang } from "@/lib/lang";
import { api, ApiError } from "@/lib/api";
import { saveSession, DEMO_API_KEY } from "@/lib/auth";
import type { BranchRead, TerminalRead, LoginResponse } from "@/lib/types";

export default function LoginPage() {
  const router = useRouter();
  const { t } = useLang();

  const [branches, setBranches] = useState<BranchRead[]>([]);
  const [terminals, setTerminals] = useState<TerminalRead[]>([]);
  const [branchId, setBranchId] = useState("");
  const [terminalId, setTerminalId] = useState("");
  const [pin, setPin] = useState("");
  const [pickerError, setPickerError] = useState<string | null>(null);
  const [manualMode, setManualMode] = useState(false);
  const [loadingPickers, setLoadingPickers] = useState(true);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [sessionExpired, setSessionExpired] = useState(false);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("reason") === "expired") setSessionExpired(true);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const key = DEMO_API_KEY || null;
        const [branchList, terminalList] = await Promise.all([
          api.get<BranchRead[]>("/v1/branches?limit=100", key),
          api.get<TerminalRead[]>("/v1/terminals?limit=100", key),
        ]);
        if (cancelled) return;
        setBranches(branchList);
        setTerminals(terminalList);
        if (branchList[0]) setBranchId(branchList[0].id);
      } catch (err) {
        if (cancelled) return;
        // Graceful fallback: only surface a setup hint on an actual auth
        // failure (missing/invalid NEXT_PUBLIC_DEMO_API_KEY); any other
        // error (API not running yet, network hiccup) gets a plain retry
        // hint. Either way the form still works via manual ID entry so a
        // plain `npm run dev`/`build` stays reviewable without that env var.
        if (err instanceof ApiError && err.status === 401) {
          setPickerError(
            "Could not list branches/terminals: the demo sandbox API key (NEXT_PUBLIC_DEMO_API_KEY) is missing or invalid. Enter IDs manually below, or set that env var and reload."
          );
        } else {
          setPickerError("Could not reach the API to load branches/terminals. Enter IDs manually below, or check the API is running.");
        }
        setManualMode(true);
      } finally {
        if (!cancelled) setLoadingPickers(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const terminalsForBranch = terminals.filter((term) => term.branch_id === branchId);

  function pressDigit(d: string) {
    setLoginError(null);
    setPin((p) => (p.length >= 6 ? p : p + d));
  }

  async function submit(pinValue: string) {
    if (!branchId) {
      setLoginError("Select or enter a branch first.");
      return;
    }
    if (pinValue.length < 4) return;
    setSubmitting(true);
    setLoginError(null);
    try {
      const resp = await api.post<LoginResponse>(
        "/v1/auth/login",
        { branch_id: branchId, terminal_id: terminalId || undefined, pin: pinValue },
        null
      );
      const branch = branches.find((b) => b.id === branchId);
      const terminal = terminals.find((tm) => tm.id === terminalId);
      saveSession({
        token: resp.access_token,
        user: resp.user,
        companyId: resp.user.company_id,
        branchId,
        branchName: branch?.name || "",
        terminalId: terminalId || "",
        terminalName: terminal?.name || "",
      });
      router.replace("/pos");
    } catch (err) {
      setLoginError(err instanceof ApiError ? err.message : "Login failed. Try again.");
      setPin("");
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    if (pin.length === 4 || pin.length === 6) {
      // Allow a brief pause in case of a 5th/6th digit for longer PINs, but
      // seeded demo PINs are 4 digits -- auto-submit at 4.
      if (pin.length === 4) submit(pin);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pin]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-ink-950 px-4 py-10">
      <div className="absolute right-6 top-6">
        <LangToggle variant="dark" />
      </div>
      <Logo className="mb-8 scale-125" />
      <div className="w-full max-w-sm rounded-2xl bg-ink-900 p-6 shadow-2xl">
        <h1 className="mb-1 text-center text-base font-semibold text-white">{t("login")}</h1>
        <p className="mb-5 text-center text-xs text-slate-400">Lahore Karahi House</p>

        {sessionExpired && (
          <div data-testid="session-expired" className="mb-4 rounded-lg bg-sky-500/10 p-3 text-xs leading-relaxed text-sky-300">
            Your session has expired or the data was reset. Please enter your PIN again.
          </div>
        )}

        {pickerError && (
          <div className="mb-4 rounded-lg bg-amber-500/10 p-3 text-xs leading-relaxed text-amber-300">
            {pickerError}
          </div>
        )}

        <div className="mb-3 space-y-3">
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-400">{t("branch")}</label>
            {!manualMode ? (
              <select
                className="input bg-ink-800 text-white border-ink-700"
                value={branchId}
                onChange={(e) => {
                  setBranchId(e.target.value);
                  setTerminalId("");
                }}
                disabled={loadingPickers}
              >
                {branches.length === 0 && <option value="">{loadingPickers ? t("loading") : "No branches"}</option>}
                {branches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name} ({b.city})
                  </option>
                ))}
              </select>
            ) : (
              <input
                className="input bg-ink-800 text-white border-ink-700"
                placeholder="branch_id"
                value={branchId}
                onChange={(e) => setBranchId(e.target.value)}
              />
            )}
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-400">{t("terminal")}</label>
            {!manualMode ? (
              <select
                className="input bg-ink-800 text-white border-ink-700"
                value={terminalId}
                onChange={(e) => setTerminalId(e.target.value)}
                disabled={loadingPickers}
              >
                <option value="">—</option>
                {terminalsForBranch.map((tm) => (
                  <option key={tm.id} value={tm.id}>
                    {tm.name} {tm.device_label ? `· ${tm.device_label}` : ""}
                  </option>
                ))}
              </select>
            ) : (
              <input
                className="input bg-ink-800 text-white border-ink-700"
                placeholder="terminal_id (optional)"
                value={terminalId}
                onChange={(e) => setTerminalId(e.target.value)}
              />
            )}
          </div>
          {!manualMode && (
            <button
              type="button"
              onClick={() => setManualMode(true)}
              className="text-xs text-slate-500 underline hover:text-slate-300"
            >
              Can&apos;t see your branch? Enter IDs manually
            </button>
          )}
        </div>

        <div className="mb-3 flex h-12 items-center justify-center gap-3">
          {[0, 1, 2, 3].map((i) => (
            <span
              key={i}
              className={`h-3.5 w-3.5 rounded-full border-2 ${
                i < pin.length ? "border-emerald-500 bg-emerald-500" : "border-slate-600"
              }`}
            />
          ))}
        </div>
        {loginError && <p className="mb-2 text-center text-xs font-medium text-rose-400">{loginError}</p>}
        {submitting && <p className="mb-2 text-center text-xs font-medium text-slate-400">{t("loading")}</p>}

        <div className="grid grid-cols-3 gap-2">
          {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => pressDigit(d)}
              disabled={submitting}
              className="rounded-xl bg-ink-800 py-4 text-xl font-semibold text-white hover:bg-ink-700 active:scale-95"
            >
              {d}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setPin("")}
            disabled={submitting}
            className="rounded-xl bg-ink-800 py-4 text-sm font-semibold text-slate-400 hover:bg-ink-700"
          >
            Clear
          </button>
          <button
            type="button"
            onClick={() => pressDigit("0")}
            disabled={submitting}
            className="rounded-xl bg-ink-800 py-4 text-xl font-semibold text-white hover:bg-ink-700 active:scale-95"
          >
            0
          </button>
          <button
            type="button"
            onClick={() => setPin((p) => p.slice(0, -1))}
            disabled={submitting}
            className="rounded-xl bg-ink-800 py-4 text-sm font-semibold text-slate-400 hover:bg-ink-700"
          >
            ⌫
          </button>
        </div>
        <p className="mt-4 text-center text-[11px] text-slate-500">Demo PINs: owner 1111 · manager 2222 · cashier 3333</p>
      </div>
    </div>
  );
}
