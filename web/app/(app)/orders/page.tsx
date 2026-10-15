"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { getSession } from "@/lib/auth";
import { api } from "@/lib/api";
import { useLang } from "@/lib/lang";
import { pkr, shortDateTime } from "@/lib/format";
import type { OrderRead } from "@/lib/types";

const STATUSES = ["open", "paid", "void", "refunded"];

export default function OrdersPage() {
  const session = getSession();
  const { t } = useLang();
  const [orders, setOrders] = useState<OrderRead[]>([]);
  const [status, setStatus] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!session) return;
    const qs = new URLSearchParams({ limit: "100", branch_id: session.branchId });
    if (status) qs.set("status", status);
    api
      .get<OrderRead[]>(`/v1/orders?${qs.toString()}`)
      .then(setOrders)
      .finally(() => setLoaded(true));
  }, [session, status]);

  const filtered = useMemo(() => {
    return orders.filter((o) => {
      if (from && o.created_at < from) return false;
      if (to && o.created_at > to) return false;
      return true;
    });
  }, [orders, from, to]);

  if (!session) return null;

  return (
    <div className="p-6">
      <div className="card mb-4 flex flex-wrap items-end gap-3 p-4">
        <div>
          <label className="mb-1 block text-xs font-semibold text-slate-500">Status</label>
          <select className="input !py-2" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold text-slate-500">From</label>
          <input type="date" className="input !py-2" value={from} onChange={(e) => setFrom(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold text-slate-500">To</label>
          <input type="date" className="input !py-2" value={to} onChange={(e) => setTo(e.target.value)} />
        </div>
      </div>

      {!loaded && <p className="text-sm text-slate-400">{t("loading")}</p>}

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Order</th>
              <th className="px-4 py-3">Time</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Fiscal</th>
              <th className="px-4 py-3 text-right">Total</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((o) => (
              <tr key={o.id} className="border-t border-slate-100 hover:bg-slate-50">
                <td className="px-4 py-3">
                  <Link href={`/orders/${o.id}`} className="font-semibold text-emerald-700 hover:underline">
                    {o.order_no || o.id.slice(0, 8)}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-500">{shortDateTime(o.created_at)}</td>
                <td className="px-4 py-3 capitalize text-slate-600">{o.order_type.replace("_", " ")}</td>
                <td className="px-4 py-3">
                  <span className={`chip ${o.status === "paid" ? "chip-ok" : o.status === "open" ? "chip-pending" : "chip-neutral"}`}>
                    {o.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`chip ${o.fiscal_status === "ok" ? "chip-ok" : o.fiscal_status === "failed" ? "chip-failed" : "chip-pending"}`}>
                    {o.fiscal_status}
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-semibold">{pkr(o.total)}</td>
              </tr>
            ))}
            {loaded && filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                  No orders match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
