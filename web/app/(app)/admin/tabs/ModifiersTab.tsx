"use client";
import { useEffect, useState } from "react";
import { getSession } from "@/lib/auth";
import { api } from "@/lib/api";
import { pkr } from "@/lib/format";
import type { ModifierGroupRead } from "@/lib/types";

export default function ModifiersTab() {
  const session = getSession();
  const [groups, setGroups] = useState<ModifierGroupRead[]>([]);
  const [groupName, setGroupName] = useState("");
  const [minSelect, setMinSelect] = useState(0);
  const [maxSelect, setMaxSelect] = useState(1);
  const [modName, setModName] = useState<Record<string, string>>({});
  const [modPrice, setModPrice] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setGroups(await api.get<ModifierGroupRead[]>("/v1/modifier-groups?limit=100"));
  }

  useEffect(() => {
    refresh();
  }, []);

  async function createGroup() {
    if (!session || !groupName) return;
    setBusy(true);
    try {
      await api.post("/v1/modifier-groups", {
        company_id: session.companyId,
        name: groupName,
        name_ur: "",
        min_select: minSelect,
        max_select: maxSelect,
      });
      setGroupName("");
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function addModifier(groupId: string) {
    const name = modName[groupId];
    if (!name) return;
    await api.post("/v1/modifiers", { group_id: groupId, name, name_ur: "", price_delta: modPrice[groupId] || 0 });
    setModName((m) => ({ ...m, [groupId]: "" }));
    setModPrice((m) => ({ ...m, [groupId]: 0 }));
    await refresh();
  }

  async function removeModifier(id: string) {
    await api.del(`/v1/modifiers/${id}`);
    await refresh();
  }

  async function removeGroup(id: string) {
    await api.del(`/v1/modifier-groups/${id}`);
    await refresh();
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <div className="space-y-3 lg:col-span-2">
        {groups.map((g) => (
          <div key={g.id} className="card p-4">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-800">
                {g.name} <span className="text-xs font-normal text-slate-400">(choose {g.min_select}-{g.max_select})</span>
              </h3>
              <button onClick={() => removeGroup(g.id)} className="text-xs text-rose-500 underline">
                Delete group
              </button>
            </div>
            <ul className="mb-2 space-y-1 text-sm">
              {g.modifiers.map((m) => (
                <li key={m.id} className="flex items-center justify-between">
                  <span>
                    {m.name} {m.price_delta > 0 && <span className="text-slate-400">+{pkr(m.price_delta)}</span>}
                  </span>
                  <button onClick={() => removeModifier(m.id)} className="text-xs text-rose-500 underline">
                    Delete
                  </button>
                </li>
              ))}
            </ul>
            <div className="flex gap-2">
              <input
                className="input !py-1.5 text-sm"
                placeholder="New modifier"
                value={modName[g.id] || ""}
                onChange={(e) => setModName((m) => ({ ...m, [g.id]: e.target.value }))}
              />
              <input
                type="number"
                className="input !w-24 !py-1.5 text-sm"
                placeholder="+Rs."
                value={modPrice[g.id] || 0}
                onChange={(e) => setModPrice((m) => ({ ...m, [g.id]: Number(e.target.value) || 0 }))}
              />
              <button onClick={() => addModifier(g.id)} className="btn-secondary !py-1.5 text-sm">
                Add
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="card p-4">
        <h3 className="mb-3 text-sm font-bold text-slate-700">New modifier group</h3>
        <div className="space-y-2">
          <input className="input !py-2" placeholder="Name" value={groupName} onChange={(e) => setGroupName(e.target.value)} />
          <div className="flex gap-2">
            <input
              type="number"
              className="input !py-2"
              placeholder="Min select"
              value={minSelect}
              onChange={(e) => setMinSelect(Number(e.target.value) || 0)}
            />
            <input
              type="number"
              className="input !py-2"
              placeholder="Max select"
              value={maxSelect}
              onChange={(e) => setMaxSelect(Number(e.target.value) || 1)}
            />
          </div>
          <button onClick={createGroup} disabled={busy} className="btn-primary w-full !py-2">
            Add group
          </button>
        </div>
      </div>
    </div>
  );
}
