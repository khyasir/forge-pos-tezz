"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, getRawText } from "@/lib/api";
import { useLang } from "@/lib/lang";
import { pkr, shortDateTime } from "@/lib/format";
import { IconBack, IconPrint } from "@/components/icons";
import type { OrderRead } from "@/lib/types";

export default function OrderDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { t } = useLang();
  const [order, setOrder] = useState<OrderRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [printing, setPrinting] = useState(false);

  useEffect(() => {
    api
      .get<OrderRead>(`/v1/orders/${params.id}`)
      .then(setOrder)
      .catch(() => setError("Order not found."));
  }, [params.id]);

  async function openReceipt() {
    setPrinting(true);
    try {
      const html = await getRawText(`/v1/orders/${params.id}/receipt.html`);
      const win = window.open("", "_blank");
      if (win) {
        win.document.write(html);
        win.document.close();
        win.focus();
        win.print();
      }
    } finally {
      setPrinting(false);
    }
  }

  if (error) return <p className="p-6 text-rose-600">{error}</p>;
  if (!order) return <p className="p-6 text-slate-400">{t("loading")}</p>;

  return (
    <div className="mx-auto max-w-3xl p-6">
      <button onClick={() => router.back()} className="mb-4 flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
        <IconBack className="h-4 w-4" /> Back
      </button>

      <div className="card p-6">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Order {order.order_no || order.id.slice(0, 8)}</h1>
            <p className="text-sm text-slate-500">{shortDateTime(order.created_at)}</p>
          </div>
          <button onClick={openReceipt} disabled={printing} className="btn-secondary">
            <IconPrint className="h-4 w-4" /> {t("receipt")}
          </button>
        </div>

        <div className="mb-4 flex flex-wrap gap-2">
          <span className={`chip ${order.status === "paid" ? "chip-ok" : "chip-pending"}`}>Server: {order.status}</span>
          <span className={`chip ${order.fiscal_status === "ok" ? "chip-ok" : order.fiscal_status === "failed" ? "chip-failed" : "chip-pending"}`}>
            FBR/PRA: {order.fiscal_status}
          </span>
          <span className={`chip ${order.erp_status === "ok" ? "chip-ok" : order.erp_status === "failed" ? "chip-failed" : "chip-pending"}`}>
            ERP: {order.erp_status}
          </span>
          <span className="chip-neutral capitalize">{order.order_type.replace("_", " ")}</span>
        </div>

        {order.fiscal_number && <p className="mb-2 text-xs text-slate-500">Fiscal #: {order.fiscal_number}</p>}
        {order.fiscal_error && <p className="mb-2 text-xs text-rose-600">Fiscal error: {order.fiscal_error}</p>}
        {order.erp_error && <p className="mb-2 text-xs text-rose-600">ERP error: {order.erp_error}</p>}

        <table className="mb-4 w-full text-sm">
          <thead className="text-left text-xs uppercase text-slate-400">
            <tr>
              <th className="py-2">Item</th>
              <th className="py-2 text-right">Qty</th>
              <th className="py-2 text-right">Price</th>
              <th className="py-2 text-right">Total</th>
            </tr>
          </thead>
          <tbody>
            {order.lines.map((l) => (
              <tr key={l.id} className="border-t border-slate-100">
                <td className="py-2">
                  {l.name_snapshot}
                  {l.modifiers.length > 0 && (
                    <div className="text-xs text-slate-400">{l.modifiers.map((m) => m.name_snapshot).join(", ")}</div>
                  )}
                  {l.notes && <div className="text-xs text-amber-600">{l.notes}</div>}
                </td>
                <td className="py-2 text-right">{l.qty}</td>
                <td className="py-2 text-right">{pkr(l.unit_price)}</td>
                <td className="py-2 text-right font-semibold">{pkr(l.line_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="ml-auto max-w-xs space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-500">{t("subtotal")}</span>
            <span>{pkr(order.subtotal)}</span>
          </div>
          {order.discount > 0 && (
            <div className="flex justify-between">
              <span className="text-slate-500">{t("discount")}</span>
              <span>-{pkr(order.discount)}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-slate-500">{t("tax")}</span>
            <span>{pkr(order.tax_amount)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">{t("pos_fee")}</span>
            <span>{pkr(order.pos_fee)}</span>
          </div>
          <div className="flex justify-between border-t border-slate-200 pt-1 text-base font-bold">
            <span>{t("total")}</span>
            <span>{pkr(order.total)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
