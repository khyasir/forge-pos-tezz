"use client";
import { useEffect, useRef } from "react";
import { preloadDemoUnsyncedOrders, runSyncOnce } from "@/lib/sync";

/** Invisible component: preloads the demo "client pending" carts once, then
 * runs the offline sync loop every 5s while mounted, and immediately when the
 * device comes back online or the tab becomes visible again. Failed rows are
 * retried automatically with exponential backoff (see lib/sync.ts). Only one
 * tab syncs at a time (Web Locks). */
export default function SyncLoop({ terminalId }: { terminalId?: string }) {
  const running = useRef(false);

  useEffect(() => {
    preloadDemoUnsyncedOrders();

    async function tick() {
      if (running.current) return;
      running.current = true;
      try {
        await runSyncOnce(terminalId);
      } catch {
        /* never let the loop die */
      } finally {
        running.current = false;
      }
    }
    const onVisible = () => document.visibilityState === "visible" && tick();

    tick();
    const interval = window.setInterval(tick, 5000);
    window.addEventListener("online", tick);
    window.addEventListener("tezz:online-changed", tick);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener("online", tick);
      window.removeEventListener("tezz:online-changed", tick);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [terminalId]);

  return null;
}
