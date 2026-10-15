// Client-side pricing preview only -- mirrors api/app/services/pricing.py
// closely enough to show a live cart total, but the server is always the
// source of truth: /orders/{id}/pay recomputes tax + POS fee itself.
import type { OrderLineIn, TaxRead } from "./types";

export function lineTotal(line: OrderLineIn): number {
  const modDelta = line.modifiers.reduce((sum, m) => sum + (m.price_delta || 0), 0);
  return Math.round((line.unit_price + modDelta) * line.qty * 100) / 100;
}

export function subtotal(lines: OrderLineIn[]): number {
  return Math.round(lines.reduce((sum, l) => sum + lineTotal(l), 0) * 100) / 100;
}

export function taxRateForPayment(tax: TaxRead | undefined, isCash: boolean): number {
  if (!tax) return 0;
  return isCash ? tax.cash_rate : tax.card_rate;
}

export const POS_FEE_PKR = 1.0;

export function estimateTotal(
  lines: OrderLineIn[],
  discount: number,
  tax: TaxRead | undefined,
  isCash: boolean
): { subtotal: number; taxAmount: number; posFee: number; total: number } {
  const sub = subtotal(lines);
  const rate = taxRateForPayment(tax, isCash);
  const taxAmount = Math.round(sub * rate * 100) / 100;
  const posFee = POS_FEE_PKR;
  const total = Math.round((sub - discount + taxAmount + posFee) * 100) / 100;
  return { subtotal: sub, taxAmount, posFee, total };
}
