// Offline-first order queue. Every order is written here FIRST (status
// LOCAL); a background loop (lib/sync.ts) then pushes it to the API.
// IndexedDB only exists in the browser, so getDB() must only ever be called
// from client code paths (event handlers / useEffect), never at module
// top-level or during server-side render.
import { openDB, type DBSchema, type IDBPDatabase } from "idb";
import type { OrderCreate, PaymentIn } from "./types";

export type LocalOrderStatus = "LOCAL" | "SYNCING" | "SYNCED" | "FAILED";

export interface LocalOrder {
  client_uuid: string;
  order: OrderCreate;
  status: LocalOrderStatus;
  attempts: number;
  last_error?: string;
  server_id?: string;
  order_no?: string;
  server_total?: number;
  order_status?: string; // server order.status (open|paid|void|refunded) once known
  fiscal_status?: string;
  fiscal_number?: string;
  fiscal_error?: string;
  erp_status?: string;
  erp_error?: string;
  created_at: string;
  updated_at: string;
  // Tender info captured at checkout time but NOT sent through
  // /sync/batch (OrderCreate has no payment fields) -- the sync loop uses
  // this to finalize payment via POST /orders/{id}/pay once the order
  // exists server-side, whether that happens immediately (online) or after
  // a later offline sync.
  pending_payment?: { payments: PaymentIn[]; customer_phone?: string };
}

interface TezzDBSchema extends DBSchema {
  orders: {
    key: string;
    value: LocalOrder;
    indexes: { "by-status": string };
  };
  meta: {
    key: string;
    value: unknown;
  };
}

let dbPromise: Promise<IDBPDatabase<TezzDBSchema>> | null = null;

export function getDB(): Promise<IDBPDatabase<TezzDBSchema>> {
  if (typeof window === "undefined" || !("indexedDB" in window)) {
    return Promise.reject(new Error("IndexedDB unavailable (server/non-browser context)"));
  }
  if (!dbPromise) {
    dbPromise = openDB<TezzDBSchema>("tezz-pos", 1, {
      upgrade(db) {
        const orders = db.createObjectStore("orders", { keyPath: "client_uuid" });
        orders.createIndex("by-status", "status");
        db.createObjectStore("meta");
      },
    });
  }
  return dbPromise;
}

function notifyChanged() {
  if (typeof window !== "undefined") window.dispatchEvent(new Event("tezz:orders-changed"));
}

export async function putLocalOrder(order: LocalOrder): Promise<void> {
  const db = await getDB();
  await db.put("orders", order);
  notifyChanged();
}

export async function getLocalOrder(clientUuid: string): Promise<LocalOrder | undefined> {
  const db = await getDB();
  return db.get("orders", clientUuid);
}

export async function listLocalOrders(): Promise<LocalOrder[]> {
  const db = await getDB();
  const all = await db.getAll("orders");
  return all.sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
}

export async function listLocalOrdersByStatus(status: LocalOrderStatus): Promise<LocalOrder[]> {
  const db = await getDB();
  return db.getAllFromIndex("orders", "by-status", status);
}

export async function getMeta<T = unknown>(key: string): Promise<T | undefined> {
  const db = await getDB();
  return db.get("meta", key) as Promise<T | undefined>;
}

export async function setMeta(key: string, value: unknown): Promise<void> {
  const db = await getDB();
  await db.put("meta", value, key);
}
