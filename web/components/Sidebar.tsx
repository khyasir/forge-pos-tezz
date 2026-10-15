"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import Logo from "./Logo";
import { useLang } from "@/lib/lang";
import { clearSession, type Session } from "@/lib/auth";
import {
  IconPos,
  IconTables,
  IconKds,
  IconOrders,
  IconSync,
  IconShifts,
  IconAdmin,
  IconLogout,
} from "./icons";

const NAV = [
  { href: "/pos", key: "nav_pos", Icon: IconPos },
  { href: "/tables", key: "nav_tables", Icon: IconTables },
  { href: "/kds", key: "nav_kds", Icon: IconKds },
  { href: "/orders", key: "nav_orders", Icon: IconOrders },
  { href: "/sync", key: "nav_sync", Icon: IconSync },
  { href: "/shifts", key: "nav_shifts", Icon: IconShifts },
  { href: "/admin", key: "nav_admin", Icon: IconAdmin },
];

export default function Sidebar({ session }: { session: Session }) {
  const pathname = usePathname();
  const router = useRouter();
  const { t } = useLang();

  function logout() {
    clearSession();
    router.replace("/login");
  }

  return (
    <aside className="flex h-full w-60 shrink-0 flex-col bg-ink-950 text-slate-300">
      <div className="flex items-center gap-2 px-5 py-5">
        <Logo />
      </div>
      <nav className="flex-1 space-y-1 px-3">
        {NAV.map(({ href, key, Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition ${
                active ? "bg-emerald-600 text-white shadow-card" : "text-slate-300 hover:bg-ink-800 hover:text-white"
              }`}
            >
              <Icon className="h-5 w-5 shrink-0" />
              {t(key)}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-ink-800 px-4 py-4">
        <div className="mb-3">
          <p className="truncate text-sm font-semibold text-white">{session.user.name}</p>
          <p className="text-xs uppercase tracking-wide text-emerald-400">{session.user.role}</p>
          <p className="truncate text-xs text-slate-500">
            {session.branchName}
            {session.terminalName ? ` · ${session.terminalName}` : ""}
          </p>
        </div>
        <button onClick={logout} className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-300 hover:bg-ink-800 hover:text-white">
          <IconLogout className="h-5 w-5" />
          {t("logout")}
        </button>
      </div>
    </aside>
  );
}
