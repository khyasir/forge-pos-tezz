"use client";
import { useEffect, useState } from "react";
import { listLocalOrders } from "./db";
import { isOnline } from "./sync";

export function useOnline(): boolean {
  const [online, setOnline] = useState(true);
  useEffect(() => {
    const update = () => setOnline(isOnline());
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    window.addEventListener("tezz:online-changed", update);
    const interval = window.setInterval(update, 3000);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
      window.removeEventListener("tezz:online-changed", update);
      window.clearInterval(interval);
    };
  }, []);
  return online;
}

export function usePendingCount(): number {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let mounted = true;
    async function refresh() {
      try {
        const all = await listLocalOrders();
        const pending = all.filter((o) => o.status !== "SYNCED").length;
        if (mounted) setCount(pending);
      } catch {
        /* IndexedDB not ready yet */
      }
    }
    refresh();
    window.addEventListener("tezz:orders-changed", refresh);
    const interval = window.setInterval(refresh, 4000);
    return () => {
      mounted = false;
      window.removeEventListener("tezz:orders-changed", refresh);
      window.clearInterval(interval);
    };
  }, []);
  return count;
}
