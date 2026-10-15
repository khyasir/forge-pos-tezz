// Background sync loop: every 10s (see components/SyncLoop.tsx), when
// online, push oldest-first unsynced local orders to /api/v1/sync/batch.
// The server upserts by client_uuid so resends are always safe.
//
// Payment finalization note: OrderCreate (and therefore /sync/batch) has no
// payment fields -- it only creates/updates the order shell. So a cart that
// was checked out (tendered, paid) gets its tender info stashed on the
// LocalOrder as `pending_payment` and, once the order exists server-side
// (immediately online, or after a later offline sync), we call
// POST /orders/{id}/pay to actually finalize it (fiscal + ERP run then).
import { api, ApiError } from "./api";
import {
  getDB,
  getMeta,
  listLocalOrders,
  putLocalOrder,
  setMeta,
  type LocalOrder,
} from "./db";
import type { OrderCreate, OrderRead, PaymentIn, SyncBatchResponse } from "./types";

const SIMULATE_OFFLINE_KEY = "tezz_simulate_offline";
const DEMO_SEEDED_KEY = "demo_unsynced_preloaded";
const BATCH_SIZE = 50;

export function isSimulatedOffline(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(SIMULATE_OFFLINE_KEY) === "1";
}

export function setSimulatedOffline(value: boolean) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(SIMULATE_OFFLINE_KEY, value ? "1" : "0");
  window.dispatchEvent(new Event("tezz:online-changed"));
}

export function isOnline(): boolean {
  if (typeof window === "undefined") return true;
  if (isSimulatedOffline()) return false;
  return navigator.onLine;
}

/** One-time preload of the seed's "client pending" demo carts into
 * IndexedDB, so the Sync Status page has pending rows before the cashier
 * rings anything up. Safe to call repeatedly (guarded by a meta flag). */
export async function preloadDemoUnsyncedOrders(): Promise<void> {
  try {
    const already = await getMeta<boolean>(DEMO_SEEDED_KEY);
    if (already) return;
    const demoOrders = await api.get<OrderCreate[]>("/v1/demo/unsynced-orders", null);
    const now = new Date().toISOString();
    for (const o of demoOrders) {
      const local: LocalOrder = {
        client_uuid: o.client_uuid,
        order: o,
        status: "LOCAL",
        attempts: 0,
        created_at: o.created_at || now,
        updated_at: now,
      };
      await putLocalOrder(local);
    }
    await setMeta(DEMO_SEEDED_KEY, true);
  } catch {
    // Backend not reachable yet (e.g. first paint before API is up) -- the
    // sync loop / a later manual refresh will not retry this by design
    // (demo-only convenience), so just swallow it.
  }
}

async function finalizePaymentIfNeeded(local: LocalOrder, serverOrder: OrderRead): Promise<OrderRead> {
  if (!local.pending_payment || serverOrder.status !== "open") return serverOrder;
  try {
    return await api.post<OrderRead>(`/v1/orders/${serverOrder.id}/pay`, {
      payments: local.pending_payment.payments,
      customer_phone: local.pending_payment.customer_phone,
    });
  } catch {
    return serverOrder; // leave as open; a manual Retry from /sync can re-attempt
  }
}

function fromServerOrder(local: LocalOrder, full: OrderRead): LocalOrder {
  return {
    ...local,
    server_id: full.id,
    order_no: full.order_no,
    server_total: full.total,
    order_status: full.status,
    fiscal_status: full.fiscal_status,
    fiscal_number: full.fiscal_number,
    erp_status: full.erp_status,
  };
}

export interface SyncRunResult {
  attempted: number;
  synced: number;
  failed: number;
  skippedOffline: boolean;
}

/** Pushes the oldest unsynced (or retryable failed) local orders. Call this
 * from the 10s interval, and also immediately after creating an order while
 * online, and from manual "Retry"/"Retry all" actions on /sync. */
export async function runSyncOnce(terminalId: string | undefined): Promise<SyncRunResult> {
  if (!isOnline()) return { attempted: 0, synced: 0, failed: 0, skippedOffline: true };

  const all = await listLocalOrders();
  const candidates = all.filter((o) => o.status === "LOCAL" || o.status === "FAILED");
  const batch = candidates
    .sort((a, b) => (a.created_at < b.created_at ? -1 : 1))
    .slice(0, BATCH_SIZE);
  if (batch.length === 0) return { attempted: 0, synced: 0, failed: 0, skippedOffline: false };

  for (const o of batch) {
    o.status = "SYNCING";
    await putLocalOrder(o);
  }

  try {
    const resp = await api.post<SyncBatchResponse>("/v1/sync/batch", {
      terminal_id: terminalId || batch[0].order.terminal_id || "",
      orders: batch.map((b) => b.order),
    });
    const byUuid = new Map(resp.results.map((r) => [r.client_uuid, r]));
    let synced = 0;
    let failed = 0;
    for (const o of batch) {
      const result = byUuid.get(o.client_uuid);
      const now = new Date().toISOString();
      if (result) {
        try {
          let full = await api.get<OrderRead>(`/v1/orders/${result.server_id}`);
          full = await finalizePaymentIfNeeded(o, full);
          await putLocalOrder({ ...fromServerOrder(o, full), status: "SYNCED", updated_at: now });
        } catch {
          await putLocalOrder({ ...o, status: "SYNCED", server_id: result.server_id, updated_at: now });
        }
        synced++;
      } else {
        await putLocalOrder({
          ...o,
          status: "FAILED",
          attempts: o.attempts + 1,
          last_error: "Server did not acknowledge this order",
          updated_at: now,
        });
        failed++;
      }
    }
    return { attempted: batch.length, synced, failed, skippedOffline: false };
  } catch (err) {
    const message = err instanceof ApiError ? err.message : "Network error while syncing";
    const now = new Date().toISOString();
    for (const o of batch) {
      await putLocalOrder({
        ...o,
        status: "FAILED",
        attempts: o.attempts + 1,
        last_error: message,
        updated_at: now,
      });
    }
    return { attempted: batch.length, synced: 0, failed: batch.length, skippedOffline: false };
  }
}

/** Retries a single row from the Sync Status page: if it never reached the
 * server, re-queues + pushes it now; if it's already on the server, retries
 * whichever downstream step (fiscal/ERP) failed. */
export async function retryOrder(clientUuid: string, terminalId: string | undefined): Promise<void> {
  const db = await getDB();
  const order = await db.get("orders", clientUuid);
  if (!order) return;
  if (order.status === "SYNCED" && order.server_id) {
    if (order.fiscal_status === "failed") {
      await api.post(`/v1/fiscal/${order.server_id}/retry`).catch(() => undefined);
    }
    if (order.erp_status === "failed") {
      await api.post(`/v1/erp/${order.server_id}/retry`).catch(() => undefined);
    }
    let full = await api.get<OrderRead>(`/v1/orders/${order.server_id}`);
    full = await finalizePaymentIfNeeded(order, full);
    await putLocalOrder({ ...fromServerOrder(order, full), status: "SYNCED", updated_at: new Date().toISOString() });
    return;
  }
  order.status = "LOCAL"; // re-queue for the next sync pass
  await putLocalOrder(order);
  await runSyncOnce(terminalId);
}

export async function retryAll(terminalId: string | undefined): Promise<void> {
  await runSyncOnce(terminalId);
  const all = await listLocalOrders();
  const needsDownstreamRetry = all.filter(
    (o) => o.status === "SYNCED" && o.server_id && (o.fiscal_status === "failed" || o.erp_status === "failed")
  );
  for (const o of needsDownstreamRetry) {
    await retryOrder(o.client_uuid, terminalId);
  }
}

/** Fast path used by the POS checkout flow when the device is online: skip
 * waiting for the 10s loop and create+pay immediately. The order is still
 * written to IndexedDB first (status SYNCING while this runs), per the
 * offline-first design -- if this throws, the caller falls back to treating
 * it as a normal queued LOCAL order. */
export async function createAndPayNow(
  order: OrderCreate,
  payments: PaymentIn[],
  customerPhone: string | undefined
): Promise<OrderRead> {
  const created = await api.post<OrderRead>("/v1/orders", order);
  return api.post<OrderRead>(`/v1/orders/${created.id}/pay`, {
    payments,
    customer_phone: customerPhone,
  });
}
