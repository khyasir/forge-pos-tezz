"use client";
import { useEffect, useState } from "react";
import { getSession } from "@/lib/auth";
import { api } from "@/lib/api";
import type { CompanyRead } from "@/lib/types";

export default function SettingsTab() {
  const session = getSession();
  const [company, setCompany] = useState<CompanyRead | null>(null);
  const [fee, setFee] = useState(0);
  const [msg, setMsg] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [importMsg, setImportMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!session) return;
    api.get<CompanyRead>(`/v1/companies/${session.companyId}`).then((c) => {
      setCompany(c);
      setFee(c.default_delivery_fee ?? 0);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function save() {
    if (!company) return;
    setMsg(null);
    try {
      const c = await api.patch<CompanyRead>(`/v1/companies/${company.id}`, { default_delivery_fee: fee });
      setCompany(c);
      setMsg("Saved");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Could not save");
    }
  }

  async function runImport() {
    setImporting(true);
    setImportMsg(null);
    try {
      const r = await api.post<Record<string, number | string>>("/v1/erp/import");
      setImportMsg(
        `Imported ${r.products} products (${r.products_with_images ?? 0} with images), ${r.modifiers} modifiers, ${r.categories} categories, ${r.customers} customers.`
      );
    } catch (e) {
      setImportMsg(e instanceof Error ? e.message : "Import failed");
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="grid max-w-3xl grid-cols-1 gap-4 md:grid-cols-2">
      <div className="card p-4">
        <h3 className="mb-1 text-sm font-bold text-slate-700">Delivery</h3>
        <p className="mb-3 text-xs text-slate-500">
          Default delivery fee for new delivery orders. The cashier can change it on each order. It is taxed with the order and shown on the receipt.
        </p>
        <label className="text-xs font-semibold text-slate-500">Default delivery fee (Rs.)</label>
        <input data-testid="default-delivery-fee" type="number" min={0} className="input mb-3 !py-2" value={fee} onChange={(e) => setFee(Math.max(0, Number(e.target.value) || 0))} />
        <button onClick={save} className="btn-primary w-full !py-2" data-testid="save-settings">
          Save
        </button>
        {msg && <p className="mt-2 text-xs text-slate-600">{msg}</p>}
      </div>
      <div className="card p-4">
        <h3 className="mb-1 text-sm font-bold text-slate-700">Odoo product sync</h3>
        <p className="mb-3 text-xs text-slate-500">
          Reads products marked &quot;Available in POS&quot; from Odoo with their images, modifiers and variant attributes. It only reads from Odoo. It works when the server is set up with ERP_PROVIDER=odoo_wags.
        </p>
        <button onClick={runImport} disabled={importing} className="btn-secondary w-full !py-2">
          {importing ? "Importing..." : "Import from Odoo now"}
        </button>
        {importMsg && <p className="mt-2 text-xs text-slate-600">{importMsg}</p>}
      </div>
    </div>
  );
}
