"use client";
import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

export type Lang = "en" | "ur";

// Simple key -> {en, ur} dictionary (not a full i18n framework, per spec).
// Covers nav, cashier screen, cart, pay dialog, order types, common actions.
const dict: Record<string, { en: string; ur: string }> = {
  app_name: { en: "Tezz POS", ur: "تیز پی او ایس" },
  nav_pos: { en: "Cashier", ur: "کیشیئر" },
  nav_tables: { en: "Tables", ur: "میزیں" },
  nav_kds: { en: "Kitchen Display", ur: "کچن ڈسپلے" },
  nav_orders: { en: "Orders", ur: "آرڈرز" },
  nav_sync: { en: "Sync Status", ur: "سنک اسٹیٹس" },
  nav_shifts: { en: "Shifts", ur: "شفٹیں" },
  nav_admin: { en: "Back Office", ur: "بیک آفس" },
  logout: { en: "Log out", ur: "لاگ آؤٹ" },
  online: { en: "Online", ur: "آن لائن" },
  offline: { en: "Offline", ur: "آف لائن" },
  pending_orders: { en: "pending", ur: "زیر التوا" },
  categories: { en: "Categories", ur: "اقسام" },
  all: { en: "All", ur: "تمام" },
  search_products: { en: "Search products...", ur: "پراڈکٹ تلاش کریں..." },
  deals: { en: "Deals", ur: "ڈیلز" },
  cart: { en: "Cart", ur: "کارٹ" },
  cart_empty: { en: "Cart is empty. Tap a product to add it.", ur: "کارٹ خالی ہے۔ پراڈکٹ شامل کریں۔" },
  notes: { en: "Notes", ur: "نوٹس" },
  discount: { en: "Discount", ur: "رعایت" },
  order_type: { en: "Order type", ur: "آرڈر کی قسم" },
  dine_in: { en: "Dine-in", ur: "ڈائن ان" },
  takeaway: { en: "Takeaway", ur: "ٹیک اوے" },
  delivery: { en: "Delivery", ur: "ڈیلیوری" },
  table: { en: "Table", ur: "میز" },
  customer_phone: { en: "Customer phone", ur: "کسٹمر فون" },
  subtotal: { en: "Subtotal", ur: "ذیلی رقم" },
  tax: { en: "Tax", ur: "ٹیکس" },
  pos_fee: { en: "POS fee", ur: "پی او ایس فیس" },
  delivery_fee: { en: "Delivery fee", ur: "Delivery fee" },
  delivery_address: { en: "Delivery address", ur: "Delivery address" },
  park_order: { en: "Park order", ur: "Park order" },
  open_orders: { en: "Open orders", ur: "Open orders" },
  no_open_orders: { en: "No other open orders", ur: "No other open orders" },
  continue_order: { en: "Continue", ur: "Continue" },
  discard: { en: "Discard", ur: "Discard" },
  current: { en: "Current", ur: "Current" },
  total: { en: "Total", ur: "کل رقم" },
  pay: { en: "Pay", ur: "ادائیگی" },
  hold: { en: "Hold", ur: "روکیں" },
  send_to_kitchen: { en: "Send to Kitchen", ur: "کچن بھیجیں" },
  cash: { en: "Cash", ur: "کیش" },
  card: { en: "Card", ur: "کارڈ" },
  raast_qr: { en: "Raast QR", ur: "راست کیو آر" },
  jazzcash: { en: "JazzCash", ur: "جاز کیش" },
  easypaisa: { en: "Easypaisa", ur: "ایزی پیسہ" },
  tendered: { en: "Tendered", ur: "ادا شدہ رقم" },
  change: { en: "Change", ur: "باقی رقم" },
  split_payment: { en: "Split payment", ur: "تقسیم شدہ ادائیگی" },
  add_tender: { en: "Add tender", ur: "ادائیگی شامل کریں" },
  confirm_payment: { en: "Confirm payment", ur: "ادائیگی کی تصدیق" },
  receipt: { en: "Receipt", ur: "رسید" },
  print: { en: "Print", ur: "پرنٹ" },
  new_order: { en: "New order", ur: "نیا آرڈر" },
  free: { en: "Free", ur: "خالی" },
  occupied: { en: "Occupied", ur: "مصروف" },
  synced: { en: "Synced", ur: "سنک ہو گیا" },
  pending: { en: "Pending", ur: "زیر التوا" },
  failed: { en: "Failed", ur: "ناکام" },
  retry: { en: "Retry", ur: "دوبارہ کوشش" },
  retry_all: { en: "Retry all", ur: "سب دوبارہ کوشش کریں" },
  simulate_offline: { en: "Simulate offline", ur: "آف لائن موڈ" },
  not_on_server: { en: "not on server yet", ur: "ابھی سرور پر نہیں" },
  open_shift: { en: "Open shift", ur: "شفٹ شروع کریں" },
  close_shift: { en: "Close shift", ur: "شفٹ بند کریں" },
  z_report: { en: "Z Report", ur: "زیڈ رپورٹ" },
  save: { en: "Save", ur: "محفوظ کریں" },
  cancel: { en: "Cancel", ur: "منسوخ" },
  add: { en: "Add", ur: "شامل کریں" },
  loading: { en: "Loading...", ur: "لوڈ ہو رہا ہے..." },
  login: { en: "Log in", ur: "لاگ ان" },
  pin: { en: "PIN", ur: "پن" },
  branch: { en: "Branch", ur: "برانچ" },
  terminal: { en: "Terminal", ur: "ٹرمینل" },
};

export type TranslationKey = keyof typeof dict;

interface LangContextValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: string) => string;
}

const LangContext = createContext<LangContextValue>({
  lang: "en",
  setLang: () => {},
  t: (key: string) => dict[key]?.en ?? key,
});

export function LangProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    const saved = window.localStorage.getItem("tezz_lang");
    if (saved === "ur" || saved === "en") setLangState(saved);
  }, []);

  const setLang = (l: Lang) => {
    setLangState(l);
    window.localStorage.setItem("tezz_lang", l);
  };

  const t = useMemo(() => {
    return (key: string) => dict[key]?.[lang] ?? dict[key]?.en ?? key;
  }, [lang]);

  const value = useMemo(() => ({ lang, setLang, t }), [lang, t]);

  return (
    <LangContext.Provider value={value}>
      {/* display:contents keeps this node out of layout/flex flow while still
          letting `dir` inherit to all descendants. */}
      <div dir={lang === "ur" ? "rtl" : "ltr"} className="contents">
        {children}
      </div>
    </LangContext.Provider>
  );
}

export function useLang() {
  return useContext(LangContext);
}
