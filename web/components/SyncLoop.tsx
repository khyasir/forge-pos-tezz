"use client";
import { useEffect, useRef } from "react";
import { preloadDemoUnsyncedOrders, runSyncOnce } from "@/lib/sync";

/** Invisible component: preloads the demo "client pending" carts once, then
 * runs the offline sync loop every 10s while mounted (i.e. while the user is
 * on any authenticated page). */
export default function SyncLoop({ terminalId }: { terminalId?: string }) {
  const running = useRef(false);

  useEffect(() => {
    preloadDemoUnsyncedOrders();

    async function tick() {
      if (running.current) return;
      running.current = true;
      try {
        await runSyncOnce(terminalId);
      } finally {
        running.current = false;
      }
    }

    tick();
    const interval = window.setInterval(tick, 10000);
    return () => window.clearInterval(interval);
  }, [terminalId]);

  return null;
}
