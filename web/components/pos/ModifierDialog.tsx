"use client";
import { useState } from "react";
import Modal from "@/components/Modal";
import { useLang } from "@/lib/lang";
import { pkr, uuid } from "@/lib/format";
import type { ModifierGroupRead, ProductRead } from "@/lib/types";
import type { CartLine } from "@/lib/cart";

export default function ModifierDialog({
  product,
  groups,
  onClose,
  onAdd,
}: {
  product: ProductRead;
  groups: ModifierGroupRead[];
  onClose: () => void;
  onAdd: (line: CartLine) => void;
}) {
  const { lang, t } = useLang();
  const applicableIds = product.modifier_group_ids.split(",").map((s) => s.trim()).filter(Boolean);
  const applicable = groups.filter((g) => applicableIds.includes(g.id));
  const [selected, setSelected] = useState<Record<string, string[]>>({});
  const [qty, setQty] = useState(1);
  const [notes, setNotes] = useState("");

  function toggle(group: ModifierGroupRead, modId: string) {
    setSelected((prev) => {
      const current = prev[group.id] || [];
      const already = current.includes(modId);
      let next: string[];
      if (group.max_select <= 1) {
        next = already ? [] : [modId];
      } else if (already) {
        next = current.filter((id) => id !== modId);
      } else if (current.length >= group.max_select) {
        next = current;
      } else {
        next = [...current, modId];
      }
      return { ...prev, [group.id]: next };
    });
  }

  const deltaTotal = applicable.reduce((sum, g) => {
    const picks = selected[g.id] || [];
    return sum + picks.reduce((s, id) => s + (g.modifiers.find((m) => m.id === id)?.price_delta || 0), 0);
  }, 0);

  const canConfirm = applicable.every((g) => (selected[g.id] || []).length >= g.min_select);

  function confirm() {
    const modifiers = applicable.flatMap((g) =>
      (selected[g.id] || []).map((id) => {
        const m = g.modifiers.find((mm) => mm.id === id)!;
        return {
          modifier_id: m.id,
          name_snapshot: lang === "ur" && m.name_ur ? m.name_ur : m.name,
          price_delta: m.price_delta,
        };
      })
    );
    onAdd({
      uid: uuid(),
      product_id: product.id,
      name_snapshot: lang === "ur" && product.name_ur ? product.name_ur : product.name,
      unit_price: product.price,
      qty,
      notes,
      modifiers,
    });
    onClose();
  }

  return (
    <Modal title={lang === "ur" && product.name_ur ? product.name_ur : product.name} onClose={onClose}>
      <div className="space-y-5">
        {applicable.map((g) => (
          <div key={g.id}>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-700">{lang === "ur" && g.name_ur ? g.name_ur : g.name}</h3>
              <span className="text-xs text-slate-400">
                {g.min_select > 0
                  ? `Choose ${g.min_select}${g.max_select > g.min_select ? `-${g.max_select}` : ""}`
                  : `Up to ${g.max_select}`}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {g.modifiers.map((m) => {
                const picked = (selected[g.id] || []).includes(m.id);
                return (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => toggle(g, m.id)}
                    className={`rounded-xl border px-3 py-2 text-left text-sm transition ${
                      picked ? "border-emerald-500 bg-emerald-50 text-emerald-700" : "border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    <div className="font-medium">{lang === "ur" && m.name_ur ? m.name_ur : m.name}</div>
                    {m.price_delta > 0 && <div className="text-xs text-slate-400">+{pkr(m.price_delta)}</div>}
                  </button>
                );
              })}
            </div>
          </div>
        ))}

        <div>
          <label className="mb-1 block text-sm font-semibold text-slate-700">{t("notes")}</label>
          <input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="e.g. less spicy" />
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button type="button" className="btn-secondary !px-3 !py-2" onClick={() => setQty((q) => Math.max(1, q - 1))}>
              -
            </button>
            <span className="w-6 text-center font-semibold">{qty}</span>
            <button type="button" className="btn-secondary !px-3 !py-2" onClick={() => setQty((q) => q + 1)}>
              +
            </button>
          </div>
          <div className="text-lg font-bold text-slate-900">{pkr((product.price + deltaTotal) * qty)}</div>
        </div>

        <button disabled={!canConfirm} onClick={confirm} className="btn-primary w-full">
          {t("add")}
        </button>
      </div>
    </Modal>
  );
}
