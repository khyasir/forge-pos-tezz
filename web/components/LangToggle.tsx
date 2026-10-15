"use client";
import { useLang } from "@/lib/lang";

export default function LangToggle({ variant = "light" }: { variant?: "light" | "dark" }) {
  const { lang, setLang } = useLang();
  const base = variant === "dark" ? "bg-slate-800/70 text-slate-300" : "bg-slate-100 text-slate-500";
  return (
    <div className={`inline-flex rounded-full p-1 text-xs font-semibold ${base}`}>
      <button
        onClick={() => setLang("en")}
        className={`rounded-full px-3 py-1 transition ${lang === "en" ? "bg-emerald-500 text-white" : ""}`}
      >
        EN
      </button>
      <button
        onClick={() => setLang("ur")}
        className={`rounded-full px-3 py-1 transition ${lang === "ur" ? "bg-emerald-500 text-white" : ""}`}
      >
        اردو
      </button>
    </div>
  );
}
