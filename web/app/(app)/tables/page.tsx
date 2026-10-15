"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { getSession } from "@/lib/auth";
import { api } from "@/lib/api";
import { useLang } from "@/lib/lang";
import type { FloorRead } from "@/lib/types";

export default function TablesPage() {
  const session = getSession();
  const { t } = useLang();
  const router = useRouter();
  const [floors, setFloors] = useState<FloorRead[]>([]);
  const [activeFloor, setActiveFloor] = useState<string>("");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!session) return;
    api
      .get<FloorRead[]>("/v1/floors?limit=50")
      .then((all) => {
        const mine = all.filter((f) => f.branch_id === session.branchId);
        setFloors(mine);
        if (mine[0]) setActiveFloor(mine[0].id);
      })
      .finally(() => setLoaded(true));
  }, [session]);

  const current = useMemo(() => floors.find((f) => f.id === activeFloor), [floors, activeFloor]);

  if (!session) return null;

  return (
    <div className="p-6">
      <div className="mb-4 flex gap-2">
        {floors.map((f) => (
          <button
            key={f.id}
            onClick={() => setActiveFloor(f.id)}
            className={`rounded-full px-4 py-2 text-sm font-semibold ${
              activeFloor === f.id ? "bg-emerald-600 text-white" : "bg-white text-slate-600 border border-slate-200"
            }`}
          >
            {f.name}
          </button>
        ))}
      </div>

      {!loaded && <p className="text-sm text-slate-400">{t("loading")}</p>}
      {loaded && floors.length === 0 && <p className="text-sm text-slate-400">No floors configured for this branch yet.</p>}

      <div className="grid grid-cols-3 gap-4 sm:grid-cols-4 md:grid-cols-6">
        {current?.tables.map((tb) => (
          <button
            key={tb.id}
            onClick={() => router.push(`/pos?table=${tb.id}`)}
            className={`card flex aspect-square flex-col items-center justify-center gap-1 ${
              tb.status === "free" ? "border-emerald-200" : "border-amber-300 bg-amber-50"
            }`}
          >
            <span className="text-lg font-bold text-slate-900">{tb.name}</span>
            <span className="text-xs text-slate-500">{tb.seats} seats</span>
            <span className={`chip ${tb.status === "free" ? "chip-ok" : "chip-pending"}`}>
              {tb.status === "free" ? t("free") : t("occupied")}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
