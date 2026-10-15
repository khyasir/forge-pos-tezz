export default function Logo({ className = "", dark = true }: { className?: string; dark?: boolean }) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <svg viewBox="0 0 24 24" className="h-7 w-7 shrink-0 text-emerald-500" fill="currentColor" aria-hidden>
        <path d="M13 2 4 14h7l-1 8 10-13h-7l1-7z" />
      </svg>
      <span className={`text-lg font-bold tracking-tight ${dark ? "text-white" : "text-slate-900"}`}>
        Tezz <span className="text-emerald-500">POS</span>
      </span>
    </div>
  );
}
