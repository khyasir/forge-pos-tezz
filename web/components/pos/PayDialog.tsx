"use client";
import { useMemo, useState } from "react";
import Modal from "@/components/Modal";
import { useLang } from "@/lib/lang";
import { pkr, uuid } from "@/lib/format";
import { estimateTotal } from "@/lib/pricing";
import type { OrderLineIn, PaymentMethodRead, PaymentIn, TaxRead } from "@/lib/types";

interface TenderRow {
  uid: string;
  payment_method_id: string;
  amount: number;
  tendered: number;
}

const METHOD_LABEL_KEY: Record<string, string> = {
  cash: "cash",
  card: "card",
  raast_qr: "raast_qr",
  jazzcash: "jazzcash",
  easypaisa: "easypaisa",
};

export default function PayDialog({
  lines,
  discount,
  tax,
  paymentMethods,
  customerPhone,
  onCustomerPhoneChange,
  onClose,
  onConfirm,
}: {
  lines: OrderLineIn[];
  discount: number;
  tax: TaxRead | undefined;
  paymentMethods: PaymentMethodRead[];
  customerPhone: string;
  onCustomerPhoneChange: (v: string) => void;
  onClose: () => void;
  onConfirm: (payments: PaymentIn[]) => Promise<void>;
}) {
  const { t } = useLang();
  const [tenders, setTenders] = useState<TenderRow[]>([]);
  const [splitMode, setSplitMode] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isCash =
    tenders.length > 0 && tenders.every((row) => paymentMethods.find((m) => m.id === row.payment_method_id)?.code === "cash");
  const estimate = useMemo(
    () => estimateTotal(lines, discount, tax, tenders.length === 0 ? true : isCash),
    [lines, discount, tax, isCash, tenders.length]
  );
  const tenderedSum = Math.round(tenders.reduce((s, r) => s + r.amount, 0) * 100) / 100;
  const remaining = Math.round((estimate.total - tenderedSum) * 100) / 100;
  const cashRow = tenders.length === 1 && paymentMethods.find((m) => m.id === tenders[0].payment_method_id)?.code === "cash" ? tenders[0] : null;
  const change = cashRow ? Math.max(0, Math.round((cashRow.tendered - cashRow.amount) * 100) / 100) : 0;

  function selectSingleMethod(methodId: string) {
    const method = paymentMethods.find((m) => m.id === methodId);
    const willBeCash = method?.code === "cash";
    const est = estimateTotal(lines, discount, tax, willBeCash);
    setTenders([{ uid: uuid(), payment_method_id: methodId, amount: est.total, tendered: est.total }]);
    setSplitMode(false);
    setError(null);
  }

  function enableSplit() {
    setSplitMode(true);
    if (tenders.length === 0) {
      const cash = paymentMethods.find((m) => m.code === "cash");
      if (cash) setTenders([{ uid: uuid(), payment_method_id: cash.id, amount: 0, tendered: 0 }]);
    }
  }

  function addTenderRow() {
    const used = new Set(tenders.map((t) => t.payment_method_id));
    const next = paymentMethods.find((m) => !used.has(m.id)) || paymentMethods[0];
    const amount = Math.max(0, remaining);
    setTenders((rows) => [...rows, { uid: uuid(), payment_method_id: next.id, amount, tendered: amount }]);
  }

  function removeTenderRow(uid: string) {
    setTenders((rows) => rows.filter((r) => r.uid !== uid));
  }

  function updateRow(uid: string, patch: Partial<TenderRow>) {
    setTenders((rows) => rows.map((r) => (r.uid === uid ? { ...r, ...patch } : r)));
  }

  function fillRemaining(uid: string) {
    updateRow(uid, { amount: Math.max(0, remaining + (tenders.find((r) => r.uid === uid)?.amount || 0)) });
  }

  const canConfirm = tenders.length > 0 && Math.abs(remaining) < 0.01 && !submitting;

  async function confirm() {
    if (!canConfirm) return;
    setSubmitting(true);
    setError(null);
    try {
      const payments: PaymentIn[] = tenders.map((row) => ({
        payment_method_id: row.payment_method_id,
        amount: row.amount,
        tendered: row.tendered || row.amount,
        reference: "",
      }));
      await onConfirm(payments);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Payment failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title={t("pay")} onClose={onClose}>
      <div className="space-y-5">
        <div className="rounded-xl bg-slate-50 p-4 text-sm">
          <Row label={t("subtotal")} value={pkr(estimate.subtotal)} />
          {discount > 0 && <Row label={t("discount")} value={`- ${pkr(discount)}`} />}
          <Row label={`${t("tax")} (${Math.round((tenders.length === 0 ? (tax?.cash_rate ?? 0) : isCash ? tax?.cash_rate ?? 0 : tax?.card_rate ?? 0) * 100)}%)`} value={pkr(estimate.taxAmount)} />
          <Row label={t("pos_fee")} value={pkr(estimate.posFee)} />
          <div className="mt-2 flex items-center justify-between border-t border-slate-200 pt-2 text-base font-bold text-slate-900">
            <span>{t("total")}</span>
            <span>{pkr(estimate.total)}</span>
          </div>
        </div>

        {!splitMode && (
          <div className="grid grid-cols-3 gap-2">
            {paymentMethods.map((m) => {
              const active = tenders.length === 1 && tenders[0].payment_method_id === m.id;
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => selectSingleMethod(m.id)}
                  className={`rounded-xl border px-2 py-3 text-sm font-semibold ${
                    active ? "border-emerald-500 bg-emerald-50 text-emerald-700" : "border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  {t(METHOD_LABEL_KEY[m.code] || m.code) || m.name}
                </button>
              );
            })}
          </div>
        )}

        {cashRow && !splitMode && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-500">{t("tendered")}</label>
              <input
                type="number"
                className="input"
                value={cashRow.tendered}
                onChange={(e) => updateRow(cashRow.uid, { tendered: Number(e.target.value) || 0 })}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-500">{t("change")}</label>
              <div className="input bg-slate-50 font-semibold text-emerald-700">{pkr(change)}</div>
            </div>
          </div>
        )}

        <button type="button" onClick={enableSplit} className="text-xs font-semibold text-emerald-700 underline">
          {t("split_payment")}
        </button>

        {splitMode && (
          <div className="space-y-2">
            {tenders.map((row) => {
              const method = paymentMethods.find((m) => m.id === row.payment_method_id);
              return (
                <div key={row.uid} className="flex items-center gap-2 rounded-xl border border-slate-200 p-2">
                  <select
                    className="input !py-2"
                    value={row.payment_method_id}
                    onChange={(e) => updateRow(row.uid, { payment_method_id: e.target.value })}
                  >
                    {paymentMethods.map((m) => (
                      <option key={m.id} value={m.id}>
                        {t(METHOD_LABEL_KEY[m.code] || m.code) || m.name}
                      </option>
                    ))}
                  </select>
                  <input
                    type="number"
                    className="input !py-2"
                    value={row.amount}
                    onChange={(e) => updateRow(row.uid, { amount: Number(e.target.value) || 0, tendered: Number(e.target.value) || 0 })}
                  />
                  <button type="button" onClick={() => fillRemaining(row.uid)} className="whitespace-nowrap text-xs text-slate-400 underline">
                    fill
                  </button>
                  {tenders.length > 1 && (
                    <button type="button" onClick={() => removeTenderRow(row.uid)} className="text-rose-500">
                      ×
                    </button>
                  )}
                  {method?.code === "cash" && null}
                </div>
              );
            })}
            <button type="button" onClick={addTenderRow} className="btn-secondary w-full !py-2 text-sm">
              {t("add_tender")}
            </button>
          </div>
        )}

        <div>
          <label className="mb-1 block text-sm font-semibold text-slate-700">{t("customer_phone")}</label>
          <input
            className="input"
            value={customerPhone}
            onChange={(e) => onCustomerPhoneChange(e.target.value)}
            placeholder="03xx-xxxxxxx"
          />
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-500">Tendered: {pkr(tenderedSum)}</span>
          <span className={remaining === 0 ? "text-emerald-600" : "font-semibold text-rose-600"}>
            {remaining > 0 ? `Remaining: ${pkr(remaining)}` : remaining < 0 ? `Over: ${pkr(-remaining)}` : "Fully tendered"}
          </span>
        </div>

        {error && <p className="text-sm font-medium text-rose-600">{error}</p>}

        <button disabled={!canConfirm} onClick={confirm} className="btn-primary w-full">
          {submitting ? t("loading") : t("confirm_payment")}
        </button>
      </div>
    </Modal>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-0.5 text-slate-600">
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}
