"use client";
import { useEffect, useState } from "react";
import { getSession, DEMO_API_KEY } from "@/lib/auth";
import { api } from "@/lib/api";
import { shortDateTime } from "@/lib/format";
import type { ApiKeyRead } from "@/lib/types";

export default function ApiKeysTab() {
  const session = getSession();
  const [keys, setKeys] = useState<ApiKeyRead[]>([]);
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);

  async function refresh() {
    setKeys(await api.get<ApiKeyRead[]>("/v1/api-keys?limit=50"));
  }

  useEffect(() => {
    refresh();
  }, []);

  async function create() {
    if (!session || !label) return;
    setBusy(true);
    try {
      await api.post("/v1/api-keys", { company_id: session.companyId, label, scopes: "read,write", active: true, sandbox: true });
      setLabel("");
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  function copy(key: string) {
    navigator.clipboard?.writeText(key).then(() => {
      setCopied(key);
      setTimeout(() => setCopied(null), 1500);
    });
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <div className="card p-4 lg:col-span-2">
        <h3 className="mb-3 text-sm font-bold text-slate-700">Sandbox API keys</h3>
        <p className="mb-3 text-xs text-slate-500">
          The demo sandbox key used by the <code>/login</code> branch/terminal picker (before PIN login) is{" "}
          <code className="rounded bg-slate-100 px-1 py-0.5">{DEMO_API_KEY}</code>. It must match an active row below.
        </p>
        <ul className="divide-y divide-slate-100 text-sm">
          {keys.map((k) => (
            <li key={k.id} className="flex items-center justify-between py-2">
              <div>
                <p className="font-semibold text-slate-800">
                  {k.label} {k.key === DEMO_API_KEY && <span className="chip-ok ml-1">demo key</span>}
                </p>
                <p className="font-mono text-xs text-slate-400">{k.key}</p>
                <p className="text-xs text-slate-300">created {shortDateTime(k.created_at)}</p>
              </div>
              <button onClick={() => copy(k.key)} className="btn-secondary !px-3 !py-1.5 text-xs">
                {copied === k.key ? "Copied!" : "Copy"}
              </button>
            </li>
          ))}
        </ul>
      </div>
      <div className="card p-4">
        <h3 className="mb-3 text-sm font-bold text-slate-700">New key</h3>
        <div className="space-y-2">
          <input className="input !py-2" placeholder="Label" value={label} onChange={(e) => setLabel(e.target.value)} />
          <button onClick={create} disabled={busy} className="btn-primary w-full !py-2">
            Generate key
          </button>
        </div>
      </div>
    </div>
  );
}
