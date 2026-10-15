"use client";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import SyncLoop from "@/components/SyncLoop";
import { getSession, type Session } from "@/lib/auth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [session, setSession] = useState<Session | null | undefined>(undefined);

  useEffect(() => {
    const s = getSession();
    if (!s) {
      router.replace("/login");
      return;
    }
    setSession(s);
  }, [router]);

  if (session === undefined) {
    return <div className="flex h-screen items-center justify-center bg-slate-100 text-slate-400">Loading…</div>;
  }
  if (session === null) return null;

  return (
    <div className="flex h-screen w-full overflow-hidden bg-slate-100">
      <Sidebar session={session} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header pathname={pathname} />
        <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>
      </div>
      <SyncLoop terminalId={session.terminalId} />
    </div>
  );
}
