"use client";
import { useLang } from "@/lib/lang";
import { useOnline, usePendingCount } from "@/lib/hooks";
import LangToggle from "./LangToggle";
import { IconWifi, IconWifiOff } from "./icons";

const TITLES: Record<string, string> = {
  "/pos": "nav_pos",
  "/tables": "nav_tables",
  "/kds": "nav_kds",
  "/orders": "nav_orders",
  "/sync": "nav_sync",
  "/shifts": "nav_shifts",
  "/admin": "nav_admin",
};

export default function Header({ pathname }: { pathname: string }) {
  const { t } = useLang();
  const online = useOnline();
  const pending = usePendingCount();
  const titleKey = Object.keys(TITLES).find((p) => pathname === p || pathname.startsWith(p + "/"));

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6">
      <h1 className="text-lg font-bold text-slate-900">{titleKey ? t(TITLES[titleKey]) : "Tezz POS"}</h1>
      <div className="flex items-center gap-3">
        <div
          className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold ${
            online ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"
          }`}
          title={online ? "Connected to the API" : "Working offline -- orders queue locally"}
        >
          {online ? <IconWifi className="h-4 w-4" /> : <IconWifiOff className="h-4 w-4" />}
          {online ? t("online") : t("offline")}
        </div>
        <div className="flex items-center gap-1.5 rounded-full bg-amber-100 px-3 py-1.5 text-xs font-semibold text-amber-700">
          {pending} {t("pending_orders")}
        </div>
        <LangToggle variant="light" />
      </div>
    </header>
  );
}
