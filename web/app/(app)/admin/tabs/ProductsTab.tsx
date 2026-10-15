"use client";
import { useEffect, useState } from "react";
import { getSession } from "@/lib/auth";
import { api } from "@/lib/api";
import { pkr } from "@/lib/format";
import type { CategoryRead, KitchenStationRead, ModifierGroupRead, ProductRead, TaxRead } from "@/lib/types";

const empty = {
  name: "",
  name_ur: "",
  category_id: "",
  tax_id: "",
  kitchen_station_id: "",
  price: 0,
  sku: "",
};

export default function ProductsTab() {
  const session = getSession();
  const [products, setProducts] = useState<ProductRead[]>([]);
  const [categories, setCategories] = useState<CategoryRead[]>([]);
  const [taxes, setTaxes] = useState<TaxRead[]>([]);
  const [stations, setStations] = useState<KitchenStationRead[]>([]);
  const [groups, setGroups] = useState<ModifierGroupRead[]>([]);
  const [form, setForm] = useState(empty);
  const [selectedGroups, setSelectedGroups] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const [p, c, tx, st, mg] = await Promise.all([
      api.get<ProductRead[]>("/v1/products?limit=200"),
      api.get<CategoryRead[]>("/v1/categories?limit=100"),
      api.get<TaxRead[]>("/v1/taxes?limit=50"),
      api.get<KitchenStationRead[]>("/v1/kitchen-stations?limit=50"),
      api.get<ModifierGroupRead[]>("/v1/modifier-groups?limit=100"),
    ]);
    setProducts(p);
    setCategories(c);
    setTaxes(tx);
    setStations(st);
    setGroups(mg);
  }

  useEffect(() => {
    refresh();
  }, []);

  function toggleGroup(id: string) {
    setSelectedGroups((prev) => (prev.includes(id) ? prev.filter((g) => g !== id) : [...prev, id]));
  }

  async function create() {
    if (!session || !form.name) return;
    setBusy(true);
    setError(null);
    try {
      await api.post("/v1/products", {
        company_id: session.companyId,
        category_id: form.category_id || null,
        tax_id: form.tax_id || null,
        kitchen_station_id: form.kitchen_station_id || null,
        name: form.name,
        name_ur: form.name_ur,
        sku: form.sku,
        price: form.price,
        modifier_group_ids: selectedGroups.join(","),
      });
      setForm(empty);
      setSelectedGroups([]);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create product");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    await api.del(`/v1/products/${id}`);
    await refresh();
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <div className="card p-4 lg:col-span-2">
        <h3 className="mb-3 text-sm font-bold text-slate-700">Products ({products.length})</h3>
        <div className="max-h-[520px] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-slate-400">
              <tr>
                <th className="py-2">Name</th>
                <th className="py-2">Category</th>
                <th className="py-2 text-right">Price</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.id} className="border-t border-slate-100">
                  <td className="py-2">{p.name}</td>
                  <td className="py-2 text-slate-500">{categories.find((c) => c.id === p.category_id)?.name || "-"}</td>
                  <td className="py-2 text-right">{pkr(p.price)}</td>
                  <td className="py-2 text-right">
                    <button onClick={() => remove(p.id)} className="text-xs text-rose-500 underline">
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card p-4">
        <h3 className="mb-3 text-sm font-bold text-slate-700">New product</h3>
        <div className="space-y-2">
          <input className="input !py-2" placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input
            className="input !py-2"
            placeholder="Name (Urdu)"
            value={form.name_ur}
            onChange={(e) => setForm({ ...form, name_ur: e.target.value })}
          />
          <select className="input !py-2" value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })}>
            <option value="">Category...</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <select className="input !py-2" value={form.tax_id} onChange={(e) => setForm({ ...form, tax_id: e.target.value })}>
            <option value="">Tax...</option>
            {taxes.map((tx) => (
              <option key={tx.id} value={tx.id}>
                {tx.name}
              </option>
            ))}
          </select>
          <select
            className="input !py-2"
            value={form.kitchen_station_id}
            onChange={(e) => setForm({ ...form, kitchen_station_id: e.target.value })}
          >
            <option value="">Kitchen station...</option>
            {stations.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          <input
            type="number"
            className="input !py-2"
            placeholder="Price"
            value={form.price}
            onChange={(e) => setForm({ ...form, price: Number(e.target.value) || 0 })}
          />
          <input className="input !py-2" placeholder="SKU" value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} />
          <div>
            <p className="mb-1 text-xs font-semibold text-slate-500">Modifier groups</p>
            <div className="flex flex-wrap gap-1">
              {groups.map((g) => (
                <button
                  key={g.id}
                  type="button"
                  onClick={() => toggleGroup(g.id)}
                  className={`rounded-full px-2 py-1 text-xs ${
                    selectedGroups.includes(g.id) ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-600"
                  }`}
                >
                  {g.name}
                </button>
              ))}
            </div>
          </div>
          {error && <p className="text-xs text-rose-600">{error}</p>}
          <button onClick={create} disabled={busy} className="btn-primary w-full !py-2">
            Add product
          </button>
        </div>
      </div>
    </div>
  );
}
