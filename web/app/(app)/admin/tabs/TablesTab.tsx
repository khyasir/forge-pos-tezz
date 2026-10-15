"use client";
import { useEffect, useState } from "react";
import { getSession } from "@/lib/auth";
import { api } from "@/lib/api";
import type { FloorRead } from "@/lib/types";

export default function TablesTab() {
  const session = getSession();
  const [floors, setFloors] = useState<FloorRead[]>([]);
  const [floorName, setFloorName] = useState("");
  const [tableName, setTableName] = useState<Record<string, string>>({});
  const [tableSeats, setTableSeats] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);

  async function refresh() {
    if (!session) return;
    const all = await api.get<FloorRead[]>("/v1/floors?limit=50");
    setFloors(all.filter((f) => f.branch_id === session.branchId));
  }

  useEffect(() => {
    refresh();
  }, [session?.branchId]);

  async function createFloor() {
    if (!session || !floorName) return;
    setBusy(true);
    try {
      await api.post("/v1/floors", { branch_id: session.branchId, name: floorName });
      setFloorName("");
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function addTable(floorId: string) {
    const name = tableName[floorId];
    if (!name) return;
    await api.post("/v1/tables", { floor_id: floorId, name, seats: tableSeats[floorId] || 4 });
    setTableName((m) => ({ ...m, [floorId]: "" }));
    await refresh();
  }

  async function removeTable(id: string) {
    await api.del(`/v1/tables/${id}`);
    await refresh();
  }

  if (!session) return null;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <div className="space-y-3 lg:col-span-2">
        {floors.map((f) => (
          <div key={f.id} className="card p-4">
            <h3 className="mb-2 text-sm font-bold text-slate-800">{f.name}</h3>
            <div className="mb-2 flex flex-wrap gap-2">
              {f.tables.map((tb) => (
                <span key={tb.id} className="flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1 text-xs">
                  {tb.name} ({tb.seats})
                  <button onClick={() => removeTable(tb.id)} className="text-rose-500">
                    ×
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                className="input !py-1.5 text-sm"
                placeholder="Table name (e.g. T9)"
                value={tableName[f.id] || ""}
                onChange={(e) => setTableName((m) => ({ ...m, [f.id]: e.target.value }))}
              />
              <input
                type="number"
                className="input !w-20 !py-1.5 text-sm"
                placeholder="Seats"
                value={tableSeats[f.id] || 4}
                onChange={(e) => setTableSeats((m) => ({ ...m, [f.id]: Number(e.target.value) || 4 }))}
              />
              <button onClick={() => addTable(f.id)} className="btn-secondary !py-1.5 text-sm">
                Add table
              </button>
            </div>
          </div>
        ))}
      </div>
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-bold text-slate-700">New floor</h3>
        <div className="space-y-2">
          <input className="input !py-2" placeholder="Name (e.g. Rooftop)" value={floorName} onChange={(e) => setFloorName(e.target.value)} />
          <button onClick={createFloor} disabled={busy} className="btn-primary w-full !py-2">
            Add floor
          </button>
        </div>
      </div>
    </div>
  );
}
