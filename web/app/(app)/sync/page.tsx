"use client";
import { useCallback, useEffect, useState } from "react";
import { getSession } from "@/lib/auth";
import { api } from "@/lib/api";
import { useLang } from "@/lib/lang";
import { pkr, shortDateTime } from "@/lib/format";
import { listLocalOrders, type LocalOrder } from "@/lib/db";
import { isSimulatedOffline, retryAll, retryOrder, retryServerOrder, setSimulatedOffline } from "@/lib/sync";
import type { SyncStatusResponse } from "@/lib/types";

export default function SyncStatusPage() {
  const session = getSession();
  const { t } = useLang();
  const [serverStatus, setServerStatus] = useState<SyncStatusResponse | null>(null);
  const [localOrders, setLocalOrders] = useState<LocalOrder[]>([]);
  const [simOffline, setSimOffline] = useState(false);
  const [busyRows, setBusyRows] = useState<Record<string, boolean>>({});
  const [retryingAll, setRetryingAll] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const status = await api.get<SyncStatusResponse>("/v1/sync/status");
      setServerStatus(status);
    } catch {
      /* API offline -- local-only view still useful */
    }
    const local = await listLocalOrders();
    setLocalOrders(local);
  }, []);

  useEffect(() => {
    setSimOffline(isSimulatedOffline());
    refresh();
    const interval = window.setInterval(refresh, 6000);
    window.addEventListener("tezz:orders-changed", refresh);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener("tezz:orders-changed", refresh);
    };
  }, [refresh]);

  const localOnly = localOrders.filter((o) => o.status !== "SYNCED");
  const localFailedCount = localOnly.filter((o) => o.status === "FAILED").length;

  const synced = serverStatus?.synced ?? 0;
  const serverPending = serverStatus?.pending ?? 0;
  const serverFailed = serverStatus?.failed ?? 0;
  const pending = serverPending + (localOnly.length - localFailedCount);
  const failed = serverFailed + localFailedCount;

  function toggleSimOffline() {
    const next = !simOffline;
    setSimOffline(next);
    setSimulatedOffline(next);
  }

  async function doRetry(clientUuid: string) {
    setBusyRows((r) => ({ ...r, [clientUuid]: true }));
    try {
      await retryOrder(clientUuid, session?.terminalId);
    } finally {
      setBusyRows((r) => ({ ...r, [clientUuid]: false }));
      refresh();
    }
  }

  async function doRetryServer(orderId: string, fiscalFailed: boolean, erpFailed: boolean) {
    setBusyRows((r) => ({ ...r, [orderId]: true }));
    try {
      await retryServerOrder(orderId, fiscalFailed, erpFailed);
    } finally {
      setBusyRows((r) => ({ ...r, [orderId]: false }));
      refresh();
    }
  }

  async function doRetryAll() {
    setRetryingAll(true);
    try {
      const serverFailedIds = (serverStatus?.orders || [])
        .filter((o) => o.fiscal_status === "failed" || o.erp_status === "failed")
        .map((o) => o.order_id);
      await retryAll(session?.terminalId, serverFailedIds);
    } finally {
      setRetryingAll(false);
      refresh();
    }
  }

  if (!session) return null;

  return (
    <div className="p-6">
      <div className="mb-4 grid grid-cols-3 gap-4">
        <Counter label={t("synced")} value={synced} tone="ok" />
        <Counter label={t("pending")} value={pending} tone="pending" />
        <Counter label={t("failed")} value={failed} tone="failed" />
      </div>

      <div className="mb-4 flex items-center justify-between">
        <label className="flex items-center gap-2 text-sm font-semibold text-slate-600">
          <input type="checkbox" checked={simOffline} onChange={toggleSimOffline} className="h-4 w-4" />
          {t("simulate_offline")}
        </label>
        <button onClick={doRetryAll} disabled={retryingAll} className="btn-primary">
          {retryingAll ? t("loading") : t("retry_all")}
        </button>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Order</th>
              <th className="px-4 py-3">Time</th>
              <th className="px-4 py-3 text-right">Amount</th>
              <th className="px-4 py-3">Server</th>
              <th className="px-4 py-3">FBR/PRA</th>
              <th className="px-4 py-3">ERP</th>
              <th className="px-4 py-3">Error</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {localOnly.map((o) => (
              <tr key={o.client_uuid} data-testid="local-row" data-status={o.status} className="border-t border-slate-100">
                <td className="px-4 py-3 font-medium text-slate-700">(local) {o.client_uuid.slice(0, 8)}</td>
                <td className="px-4 py-3 text-slate-500">{shortDateTime(o.created_at)}</td>
                <td className="px-4 py-3 text-right">
                  {pkr(o.order.lines.reduce((s, l) => s + l.unit_price * l.qty, 0))}
                </td>
                <td className="px-4 py-3">
                  <span className={`chip ${o.status === "FAILED" ? "chip-failed" : "chip-neutral"}`}>
                    {o.status === "FAILED" ? t("failed") : t("not_on_server")}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="chip-neutral">not synced</span>
                </td>
                <td className="px-4 py-3">
                  <span className="chip-neutral">not synced</span>
                </td>
                <td className="px-4 py-3 max-w-[220px] text-xs text-rose-600">
                  <span className="block truncate">{o.last_error || ""}</span>
                  {o.rejected ? (
                    <span className="block text-slate-500">Will not retry automatically</span>
                  ) : o.status === "FAILED" && o.next_attempt_at ? (
                    <span className="block text-slate-500">Auto-retry at {new Date(o.next_attempt_at).toLocaleTimeString()}</span>
                  ) : null}
                </td>
                <td className="px-4 py-3">
                  <button onClick={() => doRetry(o.client_uuid)} disabled={busyRows[o.client_uuid]} className="btn-secondary !px-3 !py-1.5 text-xs">
                    {t("retry")}
                  </button>
                </td>
              </tr>
            ))}
            {(serverStatus?.orders || []).map((o) => {
              const local = localOrders.find((l) => l.server_id === o.order_id);
              return (
                <tr key={o.order_id} className="border-t border-slate-100">
                  <td className="px-4 py-3 font-medium text-slate-700">{o.order_no}</td>
                  <td className="px-4 py-3 text-slate-500">{shortDateTime(o.created_at)}</td>
                  <td className="px-4 py-3 text-right">{pkr(o.total)}</td>
                  <td className="px-4 py-3">
                    <span className="chip-ok">synced</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`chip ${o.fiscal_status === "ok" ? "chip-ok" : o.fiscal_status === "failed" ? "chip-failed" : "chip-pending"}`}>
                      {o.fiscal_status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`chip ${o.erp_status === "ok" ? "chip-ok" : o.erp_status === "failed" ? "chip-failed" : "chip-pending"}`}>
                      {o.erp_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 max-w-[200px] truncate text-xs text-rose-600">
                    {o.fiscal_error || o.erp_error || local?.fiscal_error || local?.erp_error || ""}
                  </td>
                  <td className="px-4 py-3">
                    {(o.fiscal_status === "failed" || o.erp_status === "failed") && (
                      <button
                        onClick={() => doRetryServer(o.order_id, o.fiscal_status === "failed", o.erp_status === "failed")}
                        disabled={busyRows[o.order_id]}
                        className="btn-secondary !px-3 !py-1.5 text-xs"
                      >
                        {t("retry")}
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
            {!serverStatus && localOnly.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-slate-400">
                  {t("loading")}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Counter({ label, value, tone }: { label: string; value: number; tone: "ok" | "pending" | "failed" }) {
  const toneClass = tone === "ok" ? "text-emerald-600" : tone === "pending" ? "text-amber-600" : "text-rose-600";
  return (
    <div className="card p-5">
      <p className="text-xs font-semibold uppercase text-slate-400">{label}</p>
      <p className={`text-3xl font-bold ${toneClass}`}>{value}</p>
    </div>
  );
}
