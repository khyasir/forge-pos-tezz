// Orchestrates the "always IndexedDB first" checkout flow used by /pos.
import { putLocalOrder, type LocalOrder } from "./db";
import { createAndPayNow, isOnline } from "./sync";
import type { OrderCreate, OrderRead, PaymentIn } from "./types";

export interface CheckoutResult {
  clientUuid: string;
  synced: boolean;
  order?: OrderRead; // present only when the immediate online pay succeeded
}

export async function checkoutOrder(
  order: OrderCreate,
  payments: PaymentIn[],
  customerPhone: string | undefined
): Promise<CheckoutResult> {
  const now = new Date().toISOString();
  const online = isOnline();
  const fullOrder: OrderCreate = { ...order, offline: !online };

  const local: LocalOrder = {
    client_uuid: order.client_uuid,
    order: fullOrder,
    status: online ? "SYNCING" : "LOCAL",
    attempts: 0,
    created_at: order.created_at || now,
    updated_at: now,
    pending_payment: { payments, customer_phone: customerPhone },
  };
  // ALWAYS write to IndexedDB first, before any network attempt.
  await putLocalOrder(local);

  if (!online) {
    return { clientUuid: order.client_uuid, synced: false };
  }

  try {
    const paid = await createAndPayNow(fullOrder, payments, customerPhone);
    await putLocalOrder({
      ...local,
      status: "SYNCED",
      server_id: paid.id,
      order_no: paid.order_no,
      server_total: paid.total,
      order_status: paid.status,
      fiscal_status: paid.fiscal_status,
      fiscal_number: paid.fiscal_number,
      erp_status: paid.erp_status,
      updated_at: new Date().toISOString(),
    });
    return { clientUuid: order.client_uuid, synced: true, order: paid };
  } catch {
    // Immediate attempt failed (network blip, server hiccup) -- leave it
    // LOCAL so the 10s background loop retries via /sync/batch.
    await putLocalOrder({ ...local, status: "LOCAL", updated_at: new Date().toISOString() });
    return { clientUuid: order.client_uuid, synced: false };
  }
}
