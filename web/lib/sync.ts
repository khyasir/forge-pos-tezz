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
const STALE_SYNCING_MS = 2 * 60 * 1000; // tab crashed/closed mid-sync -> retry
const MAX_BACKOFF_MS = 5 * 60 * 1000;

function staleSyncingMs(): number {
  // test hook: e2e tests shorten this to simulate "crash mid-sync" recovery quickly
  const v = typeof window !== "undefined" ? Number(window.localStorage.getItem("tezz_stale_syncing_ms")) : 0;
  return v > 0 ? v : STALE_SYNCING_MS;
}

/** 5s, 10s, 20s, 40s ... capped at 5 minutes. */
export function backoffMs(attempts: number): number {
  return Math.min(5000 * 2 ** Math.max(0, attempts - 1), MAX_BACKOFF_MS);
}

function failed(o: LocalOrder, message: string): LocalOrder {
  const attempts = o.attempts + 1;
  return {
    ...o,
    status: "FAILED",
    attempts,
    last_error: message,
    next_attempt_at: new Date(Date.now() + backoffMs(attempts)).toISOString(),
    updated_at: new Date().toISOString(),
  };
}

/** Only one tab/window syncs at a time (Web Locks API); others skip the tick. */
async function withSyncLock<T>(fn: () => Promise<T>, fallback: T): Promise<T> {
  const locks = typeof navigator !== "undefined" ? (navigator as Navigator & { locks?: LockManager }).locks : undefined;
  if (!locks) return fn();
  let ran = false;
  const result = await locks.request("tezz-sync", { ifAvailable: true }, async (lock) => {
    if (!lock) return fallback;
    ran = true;
    return fn();
  });
  return ran ? (result as T) : fallback;
}

export function isDue(o: LocalOrder, now = Date.now()): boolean {
  if (o.rejected) return false;
  if (o.status === "LOCAL") return true;
  if (o.status === "FAILED") return !o.next_attempt_at || Date.parse(o.next_attempt_at) <= now;
  if (o.status === "SYNCING") return now - Date.parse(o.updated_at) > staleSyncingMs();
  // Reached the server but payment was not finalized yet (e.g. network dropped between create and pay)
  if (o.status === "SYNCED" && o.pending_payment && o.order_status === "open") return true;
  return false;
}

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
  } catch (err) {
    // 400 = someone (another tab, an earlier attempt whose response was lost)
    // already paid it. The server is the source of truth: re-read it.
    if (err instanceof ApiError && err.status === 400) return api.get<OrderRead>(`/v1/orders/${serverOrder.id}`);
    throw err; // network error: caller marks FAILED and the loop retries with backoff
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
    fiscal_error: full.fiscal_error,
    erp_status: full.erp_status,
    erp_error: full.erp_error,
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
export async function runSyncOnce(terminalId: string | undefined, opts: { force?: boolean } = {}): Promise<SyncRunResult> {
  if (!isOnline()) return { attempted: 0, synced: 0, failed: 0, skippedOffline: true };
  return withSyncLock(() => syncPass(terminalId, !!opts.force), { attempted: 0, synced: 0, failed: 0, skippedOffline: false });
}

async function syncPass(terminalId: string | undefined, force: boolean): Promise<SyncRunResult> {
  const all = await listLocalOrders();
  const now = Date.now();
  const candidates = all.filter((o) => (force ? !o.rejected && o.status !== "SYNCED" : isDue(o, now)) || isDue(o, now));
  const batch = candidates
    .sort((a, b) => (a.created_at < b.created_at ? -1 : 1))
    .slice(0, BATCH_SIZE);
  if (batch.length === 0) {
    await refreshDownstream();
    return { attempted: 0, synced: 0, failed: 0, skippedOffline: false };
  }

  for (const o of batch) {
    o.status = o.status === "SYNCED" ? "SYNCED" : "SYNCING";
    o.updated_at = new Date().toISOString();
    await putLocalOrder(o);
  }

  let resp: SyncBatchResponse;
  try {
    resp = await api.post<SyncBatchResponse>("/v1/sync/batch", {
      terminal_id: terminalId || batch[0].order.terminal_id || "",
      orders: batch.map((b) => b.order),
    });
  } catch (err) {
    const message = err instanceof ApiError ? err.message : "Network error while syncing";
    for (const o of batch) await putLocalOrder(failed(o, message));
    return { attempted: batch.length, synced: 0, failed: batch.length, skippedOffline: false };
  }

  const byUuid = new Map(resp.results.map((r) => [r.client_uuid, r]));
  let synced = 0;
  let failedCount = 0;
  for (const o of batch) {
    const result = byUuid.get(o.client_uuid);
    const ts = new Date().toISOString();
    if (!result) {
      await putLocalOrder(failed(o, "Server did not acknowledge this order"));
      failedCount++;
      continue;
    }
    if (result.status === "error") {
      await putLocalOrder(failed(o, result.error || "Server error"));
      failedCount++;
      continue;
    }
    if (result.status === "rejected") {
      await putLocalOrder({ ...o, status: "FAILED", rejected: true, last_error: `Rejected by server: ${result.error}`, updated_at: ts });
      failedCount++;
      continue;
    }
    try {
      let full = await api.get<OrderRead>(`/v1/orders/${result.server_id}`);
      full = await finalizePaymentIfNeeded(o, full);
      await putLocalOrder({ ...fromServerOrder(o, full), status: "SYNCED", last_error: undefined, next_attempt_at: undefined, updated_at: ts });
      synced++;
    } catch (err) {
      // Order exists on the server but payment is not finalized yet. Keep it
      // due for retry; /sync/batch is idempotent so resending is safe.
      const message = err instanceof ApiError ? err.message : "Network error while finalizing payment";
      await putLocalOrder(failed({ ...o, server_id: result.server_id }, message));
      failedCount++;
    }
  }
  return { attempted: batch.length, synced, failed: failedCount, skippedOffline: false };
}

/** The server now retries FBR/Odoo automatically. This refreshes local rows
 * whose fiscal/ERP step was not yet ok so the Sync page shows the latest. */
async function refreshDownstream(): Promise<void> {
  const all = await listLocalOrders();
  const stale = all
    .filter((o) => o.status === "SYNCED" && o.server_id && (o.fiscal_status !== "ok" || o.erp_status !== "ok"))
    .slice(0, 10);
  for (const o of stale) {
    try {
      const full = await api.get<OrderRead>(`/v1/orders/${o.server_id}`);
      await putLocalOrder({ ...fromServerOrder(o, full), updated_at: new Date().toISOString() });
    } catch {
      return;
    }
  }
}

/** Retries whichever downstream step (fiscal/ERP) failed for an order that
 * already exists server-side. Works for rows that originated entirely on
 * the server too (e.g. the seed's 3 demo "fiscal failed" orders), which
 * have no IndexedDB record at all -- that's why this takes a server
 * order_id directly rather than requiring a local record. If a matching
 * local record exists, it's refreshed with the final statuses too. */
export async function retryServerOrder(orderId: string, fiscalFailed: boolean, erpFailed: boolean): Promise<OrderRead> {
  if (fiscalFailed) await api.post(`/v1/fiscal/${orderId}/retry`).catch(() => undefined);
  if (erpFailed) await api.post(`/v1/erp/${orderId}/retry`).catch(() => undefined);
  const full = await api.get<OrderRead>(`/v1/orders/${orderId}`);
  const local = await findLocalByServerId(orderId);
  if (local) {
    await putLocalOrder({ ...fromServerOrder(local, full), status: "SYNCED", updated_at: new Date().toISOString() });
  }
  return full;
}

async function findLocalByServerId(serverId: string): Promise<LocalOrder | undefined> {
  const all = await listLocalOrders();
  return all.find((o) => o.server_id === serverId);
}

/** Retries a single LOCAL/FAILED row from the Sync Status page that has
 * never reached the server at all: re-queues + pushes it now. */
export async function retryOrder(clientUuid: string, terminalId: string | undefined): Promise<void> {
  const db = await getDB();
  const order = await db.get("orders", clientUuid);
  if (!order) return;
  if (order.status === "SYNCED" && order.server_id) {
    await retryServerOrder(order.server_id, order.fiscal_status === "failed", order.erp_status === "failed");
    return;
  }
  order.status = "LOCAL"; // re-queue for the next sync pass
  order.next_attempt_at = undefined;
  order.rejected = false;
  await putLocalOrder(order);
  await runSyncOnce(terminalId);
}

export async function retryAll(terminalId: string | undefined, serverFailedOrderIds: string[] = []): Promise<void> {
  await runSyncOnce(terminalId, { force: true });
  const all = await listLocalOrders();
  const needsDownstreamRetry = all.filter(
    (o) => o.status === "SYNCED" && o.server_id && (o.fiscal_status === "failed" || o.erp_status === "failed")
  );
  for (const o of needsDownstreamRetry) {
    await retryOrder(o.client_uuid, terminalId);
  }
  // Also retry server-side-only failed orders (e.g. the seed's demo rows)
  // that have no local IndexedDB record to key off of.
  const alreadyHandled = new Set(needsDownstreamRetry.map((o) => o.server_id));
  for (const orderId of serverFailedOrderIds) {
    if (alreadyHandled.has(orderId)) continue;
    await retryServerOrder(orderId, true, true).catch(() => undefined);
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
  const created = await api.post<OrderRead>("/v1/orders", order); // idempotent on client_uuid
  if (created.status !== "open") return created;
  try {
    return await api.post<OrderRead>(`/v1/orders/${created.id}/pay`, {
      payments,
      customer_phone: customerPhone,
    });
  } catch (err) {
    if (err instanceof ApiError && err.status === 400) return api.get<OrderRead>(`/v1/orders/${created.id}`);
    throw err;
  }
}
