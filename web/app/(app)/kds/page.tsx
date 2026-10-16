"use client";
import { useCallback, useEffect, useState } from "react";
import { getSession } from "@/lib/auth";
import { api } from "@/lib/api";
import { shortDateTime } from "@/lib/format";
import type { KitchenStationRead, OrderRead, ProductRead } from "@/lib/types";

const ACTIVE_STATUSES = ["open", "paid"];

export default function KdsPage() {
  const session = getSession();
  const [stations, setStations] = useState<KitchenStationRead[]>([]);
  const [products, setProducts] = useState<ProductRead[]>([]);
  const [orders, setOrders] = useState<OrderRead[]>([]);
  const [loaded, setLoaded] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [st, pr, ord] = await Promise.all([
        api.get<KitchenStationRead[]>("/v1/kitchen-stations?limit=50"),
        api.getAll<ProductRead>("/v1/products"),
        api.get<OrderRead[]>(`/v1/orders?limit=100&branch_id=${session?.branchId || ""}`),
      ]);
      setStations(st);
      setProducts(pr);
      setOrders(ord.filter((o) => ACTIVE_STATUSES.includes(o.status) && o.kds_status !== "done"));
    } catch {
      /* transient -- next poll will retry */
    } finally {
      setLoaded(true);
    }
  }, [session?.branchId]);

  useEffect(() => {
    if (!session) return;
    refresh();
    const interval = window.setInterval(refresh, 7000);
    return () => window.clearInterval(interval);
  }, [session, refresh]);

  async function setStatus(order: OrderRead, status: "preparing" | "done") {
    setOrders((prev) =>
      status === "done" ? prev.filter((o) => o.id !== order.id) : prev.map((o) => (o.id === order.id ? { ...o, kds_status: status } : o))
    );
    try {
      await api.post(`/v1/orders/${order.id}/kds-status`, { kds_status: status });
    } finally {
      refresh();
    }
  }

  function productStation(productId?: string | null): string {
    if (!productId) return "unassigned";
    const p = products.find((pp) => pp.id === productId);
    return p?.kitchen_station_id || "unassigned";
  }

  if (!session) return null;

  const stationGroups = [...stations, { id: "unassigned", company_id: "", name: "Unassigned", created_at: "", updated_at: "" }];

  return (
    <div className="grid grid-cols-1 gap-4 p-6 md:grid-cols-2 xl:grid-cols-4">
      {!loaded && <p className="text-sm text-slate-400">Loading…</p>}
      {stationGroups.map((station) => {
        const ticketsHere = orders.filter((o) => o.lines.some((l) => productStation(l.product_id) === station.id));
        if (station.id === "unassigned" && ticketsHere.length === 0) return null;
        return (
          <div key={station.id} className="flex flex-col gap-3">
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">
              {station.name} <span className="text-slate-300">· {ticketsHere.length}</span>
            </h2>
            <div className="flex flex-col gap-3">
              {ticketsHere.map((order) => (
                <div key={order.id} className="card p-4">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="font-bold text-slate-900">#{order.order_no || order.client_uuid.slice(0, 6)}</span>
                    <span className="text-xs text-slate-400">{shortDateTime(order.created_at)}</span>
                  </div>
                  <span className="chip-neutral mb-2 inline-block capitalize">{order.order_type.replace("_", " ")}</span>
                  <ul className="mb-3 space-y-1 text-sm text-slate-700">
                    {order.lines
                      .filter((l) => productStation(l.product_id) === station.id)
                      .map((l) => (
                        <li key={l.id}>
                          <span className="font-semibold">{l.qty}x</span> {l.name_snapshot}
                          {l.notes && <span className="block text-xs text-amber-600">note: {l.notes}</span>}
                        </li>
                      ))}
                  </ul>
                  <div className="flex gap-2">
                    {order.kds_status !== "preparing" && (
                      <button onClick={() => setStatus(order, "preparing")} className="btn-amber flex-1 !py-2 text-xs">
                        Start
                      </button>
                    )}
                    <button onClick={() => setStatus(order, "done")} className="btn-primary flex-1 !py-2 text-xs">
                      Done
                    </button>
                  </div>
                </div>
              ))}
              {ticketsHere.length === 0 && <p className="text-xs text-slate-300">No open tickets</p>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
