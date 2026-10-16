// Open (in-progress) orders on this terminal: the current cart plus any
// parked ones. Stored in IndexedDB so they survive reload, crash and
// offline. Each ticket keeps a stable client_uuid from the moment it is
// created; that same uuid is used at checkout, so pressing Pay twice or
// retrying after a network error can never create two orders.
import { getMeta, setMeta } from "./db";
import { uuid } from "./format";
import type { CartLine } from "./cart";
import type { OrderType } from "./types";

export interface OpenTicket {
  id: string; // == client_uuid used at checkout
  label: string; // short human label, e.g. "#3 Table 4" or "#5 Delivery"
  seq: number;
  cart: CartLine[];
  orderType: OrderType;
  tableId: string;
  customerPhone: string;
  discount: number;
  deliveryFee: number | null; // null = use company default
  deliveryAddress: string;
  createdAt: string;
  updatedAt: string;
}

interface OpenState {
  activeId: string;
  tickets: OpenTicket[];
  seq: number;
}

const KEY = "open_orders_v1";
const CHANNEL = "tezz-open-orders";

export function newTicket(seq: number): OpenTicket {
  const now = new Date().toISOString();
  return {
    id: uuid(),
    label: `#${seq}`,
    seq,
    cart: [],
    orderType: "dine_in",
    tableId: "",
    customerPhone: "",
    discount: 0,
    deliveryFee: null,
    deliveryAddress: "",
    createdAt: now,
    updatedAt: now,
  };
}

export async function loadOpenState(): Promise<OpenState> {
  const s = await getMeta<OpenState>(KEY).catch(() => undefined);
  if (s && s.tickets?.length && s.tickets.some((t) => t.id === s.activeId)) return s;
  const t = newTicket((s?.seq || 0) + 1);
  return { activeId: t.id, tickets: [t], seq: t.seq };
}

export async function saveOpenState(s: OpenState): Promise<void> {
  await setMeta(KEY, s);
  try {
    new BroadcastChannel(CHANNEL).postMessage({ at: Date.now() });
  } catch {
    /* BroadcastChannel not supported */
  }
}

export function onOpenStateChangedElsewhere(cb: () => void): () => void {
  try {
    const ch = new BroadcastChannel(CHANNEL);
    ch.onmessage = () => cb();
    return () => ch.close();
  } catch {
    return () => undefined;
  }
}

export function ticketTitle(t: OpenTicket, tableName?: string): string {
  const kind = t.orderType === "delivery" ? "Delivery" : t.orderType === "takeaway" ? "Takeaway" : tableName ? tableName : "Dine-in";
  return `${t.label} ${kind}`;
}
