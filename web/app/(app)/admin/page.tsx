"use client";
import { useState } from "react";
import { useLang } from "@/lib/lang";
import ProductsTab from "./tabs/ProductsTab";
import CategoriesTab from "./tabs/CategoriesTab";
import ModifiersTab from "./tabs/ModifiersTab";
import TablesTab from "./tabs/TablesTab";
import ApiKeysTab from "./tabs/ApiKeysTab";
import SettingsTab from "./tabs/SettingsTab";

const TABS = [
  { key: "products", label: "Products" },
  { key: "categories", label: "Categories" },
  { key: "modifiers", label: "Modifiers" },
  { key: "tables", label: "Tables" },
  { key: "apikeys", label: "API Keys" },
  { key: "settings", label: "Settings" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export default function AdminPage() {
  const { t } = useLang();
  const [tab, setTab] = useState<TabKey>("products");

  return (
    <div className="p-6">
      <div className="mb-4 flex gap-2 border-b border-slate-200">
        {TABS.map((tb) => (
          <button
            key={tb.key}
            onClick={() => setTab(tb.key)}
            className={`border-b-2 px-4 py-2 text-sm font-semibold ${
              tab === tb.key ? "border-emerald-600 text-emerald-700" : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {tb.label}
          </button>
        ))}
        <a
          href="/api/docs"
          target="_blank"
          rel="noreferrer"
          className="ml-auto flex items-center px-4 py-2 text-xs font-semibold text-slate-400 underline hover:text-slate-700"
        >
          API Docs ↗
        </a>
      </div>

      {tab === "products" && <ProductsTab />}
      {tab === "categories" && <CategoriesTab />}
      {tab === "modifiers" && <ModifiersTab />}
      {tab === "tables" && <TablesTab />}
      {tab === "apikeys" && <ApiKeysTab />}
      {tab === "settings" && <SettingsTab />}
    </div>
  );
}
