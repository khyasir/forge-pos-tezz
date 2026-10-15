"use client";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getSession } from "@/lib/auth";
import { api } from "@/lib/api";
import { useLang } from "@/lib/lang";
import { pkr, uuid } from "@/lib/format";
import { cartLineTotal, cartSubtotal, toOrderLines, type CartLine } from "@/lib/cart";
import { estimateTotal } from "@/lib/pricing";
import { checkoutOrder } from "@/lib/checkout";
import ModifierDialog from "@/components/pos/ModifierDialog";
import PayDialog from "@/components/pos/PayDialog";
import ReceiptView, { type LocalReceiptSummary } from "@/components/pos/ReceiptView";
import { IconSearch, IconPlus, IconMinus } from "@/components/icons";
import type {
  CategoryRead,
  DealRead,
  FloorRead,
  ModifierGroupRead,
  OrderCreate,
  OrderRead,
  OrderType,
  PaymentIn,
  PaymentMethodRead,
  ProductRead,
  TaxRead,
} from "@/lib/types";

export default function PosPage() {
  return (
    <Suspense fallback={null}>
      <PosPageInner />
    </Suspense>
  );
}

function PosPageInner() {
  const session = getSession();
  const { lang, t } = useLang();
  const searchParams = useSearchParams();
  const presetTable = searchParams.get("table") || "";

  const [products, setProducts] = useState<ProductRead[]>([]);
  const [categories, setCategories] = useState<CategoryRead[]>([]);
  const [modifierGroups, setModifierGroups] = useState<ModifierGroupRead[]>([]);
  const [deals, setDeals] = useState<DealRead[]>([]);
  const [taxes, setTaxes] = useState<TaxRead[]>([]);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethodRead[]>([]);
  const [floors, setFloors] = useState<FloorRead[]>([]);
  const [loaded, setLoaded] = useState(false);

  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [showDeals, setShowDeals] = useState(false);
  const [search, setSearch] = useState("");
  const [modifierProduct, setModifierProduct] = useState<ProductRead | null>(null);

  const [cart, setCart] = useState<CartLine[]>([]);
  const [orderType, setOrderType] = useState<OrderType>("dine_in");
  const [tableId, setTableId] = useState(presetTable);
  const [customerPhone, setCustomerPhone] = useState("");
  const [discount, setDiscount] = useState(0);
  const [editingUid, setEditingUid] = useState<string | null>(null);

  const [payOpen, setPayOpen] = useState(false);
  const [receipt, setReceipt] = useState<{ synced: boolean; order?: OrderRead; local?: LocalReceiptSummary } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) return;
    (async () => {
      try {
        const [p, c, mg, d, tx, pm, fl] = await Promise.all([
          api.get<ProductRead[]>("/v1/products?limit=200"),
          api.get<CategoryRead[]>("/v1/categories?limit=100"),
          api.get<ModifierGroupRead[]>("/v1/modifier-groups?limit=100"),
          api.get<DealRead[]>("/v1/deals?limit=100"),
          api.get<TaxRead[]>("/v1/taxes?limit=50"),
          api.get<PaymentMethodRead[]>("/v1/payment-methods?limit=50"),
          api.get<FloorRead[]>("/v1/floors?limit=50"),
        ]);
        setProducts(p.filter((x) => x.active));
        setCategories(c.sort((a, b) => a.sort_order - b.sort_order));
        setModifierGroups(mg);
        setDeals(d.filter((x) => x.active));
        setTaxes(tx);
        setPaymentMethods(pm);
        setFloors(fl.filter((f) => f.branch_id === session.branchId));
      } catch {
        setError("Could not load the product catalog. Check the API connection.");
      } finally {
        setLoaded(true);
      }
    })();
  }, [session]);

  const defaultTax = useMemo(() => taxes.find((x) => x.is_default) || taxes[0], [taxes]);

  const filteredProducts = useMemo(() => {
    let list = products;
    if (activeCategory !== "all") list = list.filter((p) => p.category_id === activeCategory);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter((p) => p.name.toLowerCase().includes(q) || p.name_ur.includes(q) || p.sku.toLowerCase().includes(q));
    }
    return list;
  }, [products, activeCategory, search]);

  const allTables = floors.flatMap((f) => f.tables.map((tb) => ({ ...tb, floorName: f.name })));

  function addSimpleLine(opts: { product?: ProductRead; deal?: DealRead }) {
    setCart((prev) => {
      const existing = prev.find(
        (l) =>
          l.modifiers.length === 0 &&
          !l.notes &&
          ((opts.product && l.product_id === opts.product.id) || (opts.deal && l.deal_id === opts.deal.id))
      );
      if (existing) {
        return prev.map((l) => (l.uid === existing.uid ? { ...l, qty: l.qty + 1 } : l));
      }
      const line: CartLine = opts.product
        ? {
            uid: uuid(),
            product_id: opts.product.id,
            name_snapshot: lang === "ur" && opts.product.name_ur ? opts.product.name_ur : opts.product.name,
            unit_price: opts.product.price,
            qty: 1,
            notes: "",
            modifiers: [],
          }
        : {
            uid: uuid(),
            deal_id: opts.deal!.id,
            name_snapshot: lang === "ur" && opts.deal!.name_ur ? opts.deal!.name_ur : opts.deal!.name,
            unit_price: opts.deal!.price,
            qty: 1,
            notes: "",
            modifiers: [],
          };
      return [...prev, line];
    });
  }

  function productTapped(p: ProductRead) {
    const hasModifiers = p.modifier_group_ids.split(",").filter(Boolean).length > 0;
    if (hasModifiers) {
      setModifierProduct(p);
    } else {
      addSimpleLine({ product: p });
    }
  }

  function updateQty(uid: string, delta: number) {
    setCart((prev) =>
      prev
        .map((l) => (l.uid === uid ? { ...l, qty: Math.max(1, l.qty + delta) } : l))
        .filter((l) => l.qty > 0)
    );
  }

  function removeLine(uid: string) {
    setCart((prev) => prev.filter((l) => l.uid !== uid));
  }

  function updateNotes(uid: string, notes: string) {
    setCart((prev) => prev.map((l) => (l.uid === uid ? { ...l, notes } : l)));
  }

  const subtotal = cartSubtotal(cart);
  const estimate = estimateTotal(toOrderLines(cart), discount, defaultTax, true);

  function resetCart() {
    setCart([]);
    setDiscount(0);
    setCustomerPhone("");
    setTableId("");
    setOrderType("dine_in");
  }

  async function handleConfirmPayment(payments: PaymentIn[]) {
    if (!session) return;
    const clientUuid = uuid();
    const order: OrderCreate = {
      client_uuid: clientUuid,
      branch_id: session.branchId,
      terminal_id: session.terminalId || undefined,
      user_id: session.user.id,
      customer_id: undefined,
      table_id: orderType === "dine_in" ? tableId || undefined : undefined,
      order_type: orderType,
      source: "pos",
      discount,
      notes: "",
      offline: false,
      lines: toOrderLines(cart),
    };
    const result = await checkoutOrder(order, payments, customerPhone || undefined);
    const localSummary: LocalReceiptSummary = {
      orderNo: clientUuid.slice(0, 8).toUpperCase(),
      branchName: session.branchName,
      lines: cart,
      subtotal: estimate.subtotal,
      discount,
      taxAmount: estimate.taxAmount,
      posFee: estimate.posFee,
      total: estimate.total,
      createdAt: new Date().toISOString(),
    };
    setPayOpen(false);
    setReceipt(result.synced && result.order ? { synced: true, order: result.order } : { synced: false, local: localSummary });
    resetCart();
  }

  if (!session) return null;

  return (
    <div className="flex h-full">
      <div className="flex min-w-0 flex-1 flex-col p-4">
        <div className="mb-3 flex items-center gap-2">
          <div className="relative flex-1">
            <IconSearch className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              className="input pl-9"
              placeholder={t("search_products")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
          <button
            onClick={() => {
              setShowDeals(false);
              setActiveCategory("all");
            }}
            className={`whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold ${
              !showDeals && activeCategory === "all" ? "bg-emerald-600 text-white" : "bg-white text-slate-600 border border-slate-200"
            }`}
          >
            {t("categories")}
          </button>
          {categories.map((c) => (
            <button
              key={c.id}
              onClick={() => {
                setShowDeals(false);
                setActiveCategory(c.id);
              }}
              className={`whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold ${
                !showDeals && activeCategory === c.id ? "bg-emerald-600 text-white" : "bg-white text-slate-600 border border-slate-200"
              }`}
            >
              {lang === "ur" && c.name_ur ? c.name_ur : c.name}
            </button>
          ))}
          <button
            onClick={() => setShowDeals(true)}
            className={`whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold ${
              showDeals ? "bg-amber-500 text-white" : "bg-white text-slate-600 border border-slate-200"
            }`}
          >
            {t("deals")}
          </button>
        </div>

        {error && <p className="mb-2 text-sm text-rose-600">{error}</p>}
        {!loaded && <p className="text-sm text-slate-400">{t("loading")}</p>}

        <div className="grid flex-1 auto-rows-max grid-cols-2 gap-3 overflow-y-auto pb-4 sm:grid-cols-3 lg:grid-cols-4">
          {showDeals
            ? deals.map((d) => (
                <button
                  key={d.id}
                  onClick={() => addSimpleLine({ deal: d })}
                  className="card flex flex-col items-start gap-1 p-4 text-left hover:border-amber-300 hover:shadow-md"
                >
                  <span className="chip-pending">{t("deals")}</span>
                  <span className="font-semibold text-slate-900">{lang === "ur" && d.name_ur ? d.name_ur : d.name}</span>
                  <span className="text-xs text-slate-500">{d.description}</span>
                  <span className="mt-auto pt-2 font-bold text-amber-600">{pkr(d.price)}</span>
                </button>
              ))
            : filteredProducts.map((p) => (
                <button
                  key={p.id}
                  onClick={() => productTapped(p)}
                  className="card flex flex-col items-start gap-1 p-4 text-left hover:border-emerald-300 hover:shadow-md"
                >
                  <span className="font-semibold text-slate-900">{lang === "ur" && p.name_ur ? p.name_ur : p.name}</span>
                  <span className="mt-auto pt-2 font-bold text-emerald-700">{pkr(p.price)}</span>
                </button>
              ))}
        </div>
      </div>

      <div className="flex w-96 shrink-0 flex-col border-l border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-base font-bold text-slate-900">{t("cart")}</h2>

        <div className="mb-3 flex gap-2">
          {(["dine_in", "takeaway", "delivery"] as OrderType[]).map((ot) => (
            <button
              key={ot}
              onClick={() => setOrderType(ot)}
              className={`flex-1 rounded-lg px-2 py-2 text-xs font-semibold ${
                orderType === ot ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-600"
              }`}
            >
              {t(ot)}
            </button>
          ))}
        </div>

        {orderType === "dine_in" && (
          <select className="input mb-3" value={tableId} onChange={(e) => setTableId(e.target.value)}>
            <option value="">{t("table")}...</option>
            {allTables.map((tb) => (
              <option key={tb.id} value={tb.id}>
                {tb.floorName} · {tb.name} ({tb.status})
              </option>
            ))}
          </select>
        )}

        <div className="mb-3 flex-1 space-y-2 overflow-y-auto">
          {cart.length === 0 && <p className="py-8 text-center text-sm text-slate-400">{t("cart_empty")}</p>}
          {cart.map((l) => (
            <div key={l.uid} className="rounded-xl border border-slate-100 p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-slate-900">{l.name_snapshot}</p>
                  {l.modifiers.length > 0 && (
                    <p className="truncate text-xs text-slate-400">{l.modifiers.map((m) => m.name_snapshot).join(", ")}</p>
                  )}
                  {editingUid === l.uid ? (
                    <input
                      autoFocus
                      className="input mt-1 !py-1 text-xs"
                      placeholder={t("notes")}
                      value={l.notes}
                      onChange={(e) => updateNotes(l.uid, e.target.value)}
                      onBlur={() => setEditingUid(null)}
                    />
                  ) : (
                    <button onClick={() => setEditingUid(l.uid)} className="mt-0.5 text-left text-xs text-slate-400 underline">
                      {l.notes || t("notes")}
                    </button>
                  )}
                </div>
                <button onClick={() => removeLine(l.uid)} className="text-xs text-rose-500">
                  ✕
                </button>
              </div>
              <div className="mt-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button onClick={() => updateQty(l.uid, -1)} className="rounded-lg bg-slate-100 p-1.5">
                    <IconMinus className="h-3.5 w-3.5" />
                  </button>
                  <span className="w-5 text-center text-sm font-semibold">{l.qty}</span>
                  <button onClick={() => updateQty(l.uid, 1)} className="rounded-lg bg-slate-100 p-1.5">
                    <IconPlus className="h-3.5 w-3.5" />
                  </button>
                </div>
                <span className="text-sm font-bold text-slate-900">{pkr(cartLineTotal(l))}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="mb-3 space-y-2 border-t border-slate-100 pt-3">
          <div className="flex items-center gap-2">
            <label className="w-20 text-xs font-semibold text-slate-500">{t("discount")}</label>
            <input
              type="number"
              className="input !py-1.5 text-sm"
              value={discount}
              onChange={(e) => setDiscount(Math.max(0, Number(e.target.value) || 0))}
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="w-20 text-xs font-semibold text-slate-500">{t("customer_phone")}</label>
            <input
              className="input !py-1.5 text-sm"
              value={customerPhone}
              onChange={(e) => setCustomerPhone(e.target.value)}
              placeholder="03xx-xxxxxxx"
            />
          </div>
          <div className="flex items-center justify-between text-sm text-slate-600">
            <span>{t("subtotal")}</span>
            <span>{pkr(subtotal)}</span>
          </div>
          <div className="flex items-center justify-between text-base font-bold text-slate-900">
            <span>{t("total")} (est.)</span>
            <span>{pkr(estimate.total)}</span>
          </div>
        </div>

        <button disabled={cart.length === 0} onClick={() => setPayOpen(true)} className="btn-primary w-full text-lg">
          {t("pay")} · {pkr(estimate.total)}
        </button>
      </div>

      {modifierProduct && (
        <ModifierDialog
          product={modifierProduct}
          groups={modifierGroups}
          onClose={() => setModifierProduct(null)}
          onAdd={(line) => setCart((prev) => [...prev, line])}
        />
      )}

      {payOpen && (
        <PayDialog
          lines={toOrderLines(cart)}
          discount={discount}
          tax={defaultTax}
          paymentMethods={paymentMethods}
          customerPhone={customerPhone}
          onCustomerPhoneChange={setCustomerPhone}
          onClose={() => setPayOpen(false)}
          onConfirm={handleConfirmPayment}
        />
      )}

      {receipt && <ReceiptView synced={receipt.synced} order={receipt.order} local={receipt.local} onClose={() => setReceipt(null)} />}
    </div>
  );
}
