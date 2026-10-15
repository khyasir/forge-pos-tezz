"use client";
import { useCallback, useEffect, useState } from "react";
import { getSession } from "@/lib/auth";
import { api } from "@/lib/api";
import { useLang } from "@/lib/lang";
import { pkr, shortDateTime } from "@/lib/format";
import Modal from "@/components/Modal";
import type { ShiftRead, ZReport } from "@/lib/types";

export default function ShiftsPage() {
  const session = getSession();
  const { t } = useLang();
  const [shifts, setShifts] = useState<ShiftRead[]>([]);
  const [openingFloat, setOpeningFloat] = useState(5000);
  const [countedCash, setCountedCash] = useState(0);
  const [zReport, setZReport] = useState<ZReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const refresh = useCallback(async () => {
    if (!session) return;
    const list = await api.get<ShiftRead[]>(`/v1/shifts?branch_id=${session.branchId}`);
    setShifts(list);
    setLoaded(true);
  }, [session]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const openShift = shifts.find((s) => s.status === "open" && s.terminal_id === session?.terminalId) || shifts.find((s) => s.status === "open");

  async function doOpen() {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      await api.post("/v1/shifts", {
        branch_id: session.branchId,
        terminal_id: session.terminalId,
        user_id: session.user.id,
        opening_float: openingFloat,
      });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open shift");
    } finally {
      setBusy(false);
    }
  }

  async function doClose() {
    if (!openShift) return;
    setBusy(true);
    setError(null);
    try {
      const closed = await api.post<ShiftRead>(`/v1/shifts/${openShift.id}/close`, { counted_cash: countedCash });
      await refresh();
      const report = await api.get<ZReport>(`/v1/shifts/${closed.id}/z-report`);
      setZReport(report);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not close shift");
    } finally {
      setBusy(false);
    }
  }

  async function viewReport(shiftId: string) {
    const report = await api.get<ZReport>(`/v1/shifts/${shiftId}/z-report`);
    setZReport(report);
  }

  if (!session) return null;

  return (
    <div className="mx-auto max-w-3xl p-6">
      <div className="card mb-6 p-6">
        {openShift ? (
          <div>
            <h2 className="mb-1 text-lg font-bold text-slate-900">{t("close_shift")}</h2>
            <p className="mb-4 text-sm text-slate-500">
              Opened {shortDateTime(openShift.opened_at)} with float {pkr(openShift.opening_float)}
            </p>
            <label className="mb-1 block text-xs font-semibold text-slate-500">Counted cash in drawer</label>
            <input
              type="number"
              className="input mb-3"
              value={countedCash}
              onChange={(e) => setCountedCash(Number(e.target.value) || 0)}
            />
            <button onClick={doClose} disabled={busy} className="btn-danger w-full">
              {busy ? t("loading") : t("close_shift")}
            </button>
          </div>
        ) : (
          <div>
            <h2 className="mb-1 text-lg font-bold text-slate-900">{t("open_shift")}</h2>
            <p className="mb-4 text-sm text-slate-500">No shift currently open at this terminal.</p>
            <label className="mb-1 block text-xs font-semibold text-slate-500">Opening float</label>
            <input
              type="number"
              className="input mb-3"
              value={openingFloat}
              onChange={(e) => setOpeningFloat(Number(e.target.value) || 0)}
            />
            <button onClick={doOpen} disabled={busy} className="btn-primary w-full">
              {busy ? t("loading") : t("open_shift")}
            </button>
          </div>
        )}
        {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
      </div>

      <h2 className="mb-2 text-sm font-bold uppercase text-slate-500">Recent shifts</h2>
      {!loaded && <p className="text-sm text-slate-400">{t("loading")}</p>}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Opened</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Float</th>
              <th className="px-4 py-3 text-right">Over/Short</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {shifts.map((s) => (
              <tr key={s.id} className="border-t border-slate-100">
                <td className="px-4 py-3">{shortDateTime(s.opened_at)}</td>
                <td className="px-4 py-3">
                  <span className={`chip ${s.status === "open" ? "chip-pending" : "chip-neutral"}`}>{s.status}</span>
                </td>
                <td className="px-4 py-3 text-right">{pkr(s.opening_float)}</td>
                <td className="px-4 py-3 text-right">
                  {s.over_short != null ? (
                    <span className={s.over_short < 0 ? "text-rose-600" : "text-emerald-600"}>{pkr(s.over_short)}</span>
                  ) : (
                    "-"
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  {s.status === "closed" && (
                    <button onClick={() => viewReport(s.id)} className="text-xs font-semibold text-emerald-700 underline">
                      {t("z_report")}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {zReport && (
        <Modal title={t("z_report")} onClose={() => setZReport(null)}>
          <div className="space-y-2 text-sm">
            <Row label="Opening float" value={pkr(zReport.opening_float)} />
            <Row label="Orders" value={String(zReport.order_count)} />
            <Row label="Gross sales" value={pkr(zReport.gross_sales)} />
            <Row label="Discounts" value={pkr(zReport.discounts)} />
            <Row label="Tax collected" value={pkr(zReport.tax_collected)} />
            <Row label="POS fees" value={pkr(zReport.pos_fees)} />
            <Row label="Net total" value={pkr(zReport.net_total)} bold />
            <Row label="Counted cash" value={zReport.counted_cash != null ? pkr(zReport.counted_cash) : "-"} />
            <Row label="Expected cash" value={zReport.expected_cash != null ? pkr(zReport.expected_cash) : "-"} />
            <Row label="Over/short" value={zReport.over_short != null ? pkr(zReport.over_short) : "-"} bold />
            <Row label="Fiscal OK" value={String(zReport.fiscal_ok)} />
            <Row label="Fiscal failed" value={String(zReport.fiscal_failed)} />
            <div className="pt-2">
              <p className="mb-1 text-xs font-semibold uppercase text-slate-400">By payment method</p>
              {Object.entries(zReport.by_payment_method).map(([method, amount]) => (
                <Row key={method} label={method} value={pkr(amount)} />
              ))}
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className={`flex items-center justify-between ${bold ? "font-bold text-slate-900" : "text-slate-600"}`}>
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}
