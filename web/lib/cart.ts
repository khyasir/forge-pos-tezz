import type { OrderLineIn, OrderLineModifierIn } from "./types";

export interface CartLine {
  uid: string;
  product_id?: string;
  deal_id?: string;
  name_snapshot: string;
  unit_price: number;
  qty: number;
  notes: string;
  modifiers: OrderLineModifierIn[];
}

export function cartLineUnitTotal(line: CartLine): number {
  return line.unit_price + line.modifiers.reduce((s, m) => s + m.price_delta, 0);
}

export function cartLineTotal(line: CartLine): number {
  return Math.round(cartLineUnitTotal(line) * line.qty * 100) / 100;
}

export function cartSubtotal(lines: CartLine[]): number {
  return Math.round(lines.reduce((s, l) => s + cartLineTotal(l), 0) * 100) / 100;
}

export function toOrderLines(lines: CartLine[]): OrderLineIn[] {
  return lines.map((l) => ({
    product_id: l.product_id,
    deal_id: l.deal_id,
    name_snapshot: l.name_snapshot,
    qty: l.qty,
    unit_price: l.unit_price,
    notes: l.notes,
    modifiers: l.modifiers,
  }));
}
