"use client";
import { useEffect, useState } from "react";
import { getSession } from "@/lib/auth";
import { api } from "@/lib/api";
import type { CategoryRead } from "@/lib/types";

export default function CategoriesTab() {
  const session = getSession();
  const [categories, setCategories] = useState<CategoryRead[]>([]);
  const [name, setName] = useState("");
  const [nameUr, setNameUr] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setCategories(await api.get<CategoryRead[]>("/v1/categories?limit=100"));
  }

  useEffect(() => {
    refresh();
  }, []);

  async function create() {
    if (!session || !name) return;
    setBusy(true);
    try {
      await api.post("/v1/categories", { company_id: session.companyId, name, name_ur: nameUr, sort_order: categories.length });
      setName("");
      setNameUr("");
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    await api.del(`/v1/categories/${id}`);
    await refresh();
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-bold text-slate-700">Categories ({categories.length})</h3>
        <ul className="divide-y divide-slate-100">
          {categories
            .sort((a, b) => a.sort_order - b.sort_order)
            .map((c) => (
              <li key={c.id} className="flex items-center justify-between py-2 text-sm">
                <span>
                  {c.name} {c.name_ur && <span className="text-slate-400">· {c.name_ur}</span>}
                </span>
                <button onClick={() => remove(c.id)} className="text-xs text-rose-500 underline">
                  Delete
                </button>
              </li>
            ))}
        </ul>
      </div>
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-bold text-slate-700">New category</h3>
        <div className="space-y-2">
          <input className="input !py-2" placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <input className="input !py-2" placeholder="Name (Urdu)" value={nameUr} onChange={(e) => setNameUr(e.target.value)} />
          <button onClick={create} disabled={busy} className="btn-primary w-full !py-2">
            Add category
          </button>
        </div>
      </div>
    </div>
  );
}
