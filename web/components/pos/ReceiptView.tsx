"use client";
import { useEffect, useRef, useState } from "react";
import Modal from "@/components/Modal";
import { useLang } from "@/lib/lang";
import { pkr, shortDateTime } from "@/lib/format";
import { getRawText } from "@/lib/api";
import { IconPrint } from "@/components/icons";
import type { OrderRead } from "@/lib/types";
import type { CartLine } from "@/lib/cart";
import { cartLineTotal } from "@/lib/cart";

export interface LocalReceiptSummary {
  orderNo: string;
  branchName: string;
  lines: CartLine[];
  subtotal: number;
  discount: number;
  taxAmount: number;
  posFee: number;
  total: number;
  createdAt: string;
}

export default function ReceiptView({
  synced,
  order,
  local,
  onClose,
}: {
  synced: boolean;
  order?: OrderRead;
  local?: LocalReceiptSummary;
  onClose: () => void;
}) {
  const { t } = useLang();
  const [html, setHtml] = useState<string | null>(null);
  const [loading, setLoading] = useState(synced);
  const [loadError, setLoadError] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (!synced || !order) return;
    let cancelled = false;
    getRawText(`/v1/orders/${order.id}/receipt.html`)
      .then((text) => {
        if (!cancelled) setHtml(text);
      })
      .catch(() => {
        if (!cancelled) setLoadError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [synced, order]);

  function printIt() {
    if (html && iframeRef.current?.contentWindow) {
      iframeRef.current.contentWindow.print();
    } else {
      window.print();
    }
  }

  return (
    <Modal title={t("receipt")} onClose={onClose}>
      <div className="space-y-4">
        {synced && order ? (
          loading ? (
            <p className="py-10 text-center text-sm text-slate-400">{t("loading")}</p>
          ) : html && !loadError ? (
            <iframe ref={iframeRef} title="Receipt" srcDoc={html} className="h-[480px] w-full rounded-lg border border-slate-200" />
          ) : (
            <OfflineReceiptBody
              headline="Receipt generated -- preview unavailable"
              orderNo={order.order_no}
              total={order.total}
              createdAt={order.created_at}
            />
          )
        ) : local ? (
          <div id="offline-receipt" className="rounded-xl border-2 border-dashed border-amber-400 bg-amber-50 p-4 font-mono text-xs text-slate-800">
            <p className="mb-2 text-center text-sm font-bold text-amber-700">OFFLINE MODE - fiscal number pending</p>
            <p className="text-center font-sans text-sm font-semibold">{local.branchName || "Tezz POS"}</p>
            <p className="text-center text-[11px] text-slate-500">{shortDateTime(local.createdAt)} · Local #{local.orderNo}</p>
            <hr className="my-2 border-dashed border-slate-300" />
            {local.lines.map((l) => (
              <div key={l.uid} className="flex justify-between">
                <span>
                  {l.qty} x {l.name_snapshot}
                </span>
                <span>{pkr(cartLineTotal(l))}</span>
              </div>
            ))}
            <hr className="my-2 border-dashed border-slate-300" />
            <div className="flex justify-between">
              <span>Subtotal</span>
              <span>{pkr(local.subtotal)}</span>
            </div>
            {local.discount > 0 && (
              <div className="flex justify-between">
                <span>Discount</span>
                <span>-{pkr(local.discount)}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span>Tax (est.)</span>
              <span>{pkr(local.taxAmount)}</span>
            </div>
            <div className="flex justify-between">
              <span>POS fee (est.)</span>
              <span>{pkr(local.posFee)}</span>
            </div>
            <div className="mt-1 flex justify-between border-t border-dashed border-slate-400 pt-1 text-sm font-bold">
              <span>Total</span>
              <span>{pkr(local.total)}</span>
            </div>
            <p className="mt-3 text-center text-[10px] text-slate-500">
              This sale will sync automatically and be fiscalized with FBR/PRA once the device is back online.
            </p>
          </div>
        ) : null}

        <button onClick={printIt} className="btn-secondary w-full">
          <IconPrint className="h-4 w-4" /> {t("print")}
        </button>
        <button onClick={onClose} className="btn-primary w-full">
          {t("new_order")}
        </button>
      </div>
    </Modal>
  );
}

function OfflineReceiptBody({
  headline,
  orderNo,
  total,
  createdAt,
}: {
  headline: string;
  orderNo: string;
  total: number;
  createdAt: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 p-4 text-sm">
      <p className="mb-2 text-center text-xs text-slate-400">{headline}</p>
      <p className="text-center font-semibold">Order {orderNo}</p>
      <p className="text-center text-xs text-slate-500">{shortDateTime(createdAt)}</p>
      <p className="mt-2 text-center text-lg font-bold">{pkr(total)}</p>
    </div>
  );
}
