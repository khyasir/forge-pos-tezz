"""Import catalog + customers from Odoo (WAGS) into a dedicated Tezz company."""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from .. import models
from ..config import get_settings
from ..security import hash_pin

log = logging.getLogger("tezz.erp.import")
COMPANY_NAME = "Camel Step (Odoo staging)"


def _id():
    return uuid.uuid4().hex


def _upsert(db, model, company_id, erp_ref, **vals):
    q = db.query(model).filter(model.erp_ref == erp_ref)
    if hasattr(model, "company_id"):
        q = q.filter(model.company_id == company_id)
    obj = q.first()
    if obj is None:
        obj = model(id=_id(), erp_ref=erp_ref, **({"company_id": company_id} if hasattr(model, "company_id") else {}), **vals)
        db.add(obj)
    else:
        for k, v in vals.items():
            setattr(obj, k, v)
    return obj


def ensure_company(db: Session) -> models.Company:
    c = db.query(models.Company).filter(models.Company.name == COMPANY_NAME).first()
    if c:
        return c
    c = models.Company(id=_id(), name=COMPANY_NAME, address="Odoo staging (stepstaging.wags.sa)", city="Riyadh",
                       tax_authority=get_settings().default_tax_authority)
    db.add(c)
    db.flush()
    br = models.Branch(id=_id(), company_id=c.id, name="Odoo Test Branch", city="Riyadh")
    db.add(br)
    db.flush()
    db.add(models.Terminal(id=_id(), branch_id=br.id, name="Terminal 1"))
    db.add(models.User(id=_id(), company_id=c.id, name="Odoo Test Manager", role="manager", pin_hash=hash_pin("4444")))
    for name, code, mode in [("Cash", "cash", 1), ("Card", "card", 2)]:
        db.add(models.PaymentMethod(id=_id(), company_id=c.id, name=name, code=code, fiscal_payment_mode=mode))
    fl = models.Floor(id=_id(), branch_id=br.id, name="Main")
    db.add(fl)
    db.flush()
    for i in range(1, 5):
        db.add(models.Table(id=_id(), floor_id=fl.id, name=f"T{i}"))
    db.add(models.KitchenStation(id=_id(), company_id=c.id, name="Kitchen"))
    db.flush()
    return c


def run_import(db: Session, adapter) -> dict:
    company = ensure_company(db)
    cid = company.id
    stats = {}
    taxes = adapter.pull_taxes()
    tax_map = {}
    for t in taxes:
        rate = (t.get("amount") or 0) / 100.0 if t.get("amount_type", "percent") == "percent" else 0
        obj = _upsert(db, models.Tax, cid, str(t["id"]), name=t["name"], authority="ODOO", cash_rate=rate,
                      card_rate=rate, is_default=False)
        tax_map[t["id"]] = obj
    default_tax = max(tax_map.values(), key=lambda o: o.cash_rate, default=None)
    if default_tax:
        default_tax.is_default = True
    stats["taxes"] = len(taxes)
    cats = adapter.pull_categories()
    cat_map = {}
    for i, c in enumerate(cats):
        cat_map[c["id"]] = _upsert(db, models.Category, cid, str(c["id"]), name=c["name"], sort_order=c.get("sort_order") or i)
    stats["categories"] = len(cats)
    mcats, mods = adapter.pull_modifiers()
    grp_map = {}
    for g in mcats:
        grp_map[g["id"]] = _upsert(db, models.ModifierGroup, cid, str(g["id"]), name=g["name"], min_select=0, max_select=3)
    db.flush()
    mod_to_group = {}
    for m in mods:
        gid = m["pos_product_modifier_category"][0] if m.get("pos_product_modifier_category") else None
        if gid not in grp_map:
            continue
        _upsert(db, models.Modifier, cid, str(m["id"]), group_id=grp_map[gid].id, name=m["name"], price_delta=m.get("price") or 0)
        mod_to_group[m["id"]] = grp_map[gid].id
    stats["modifier_groups"] = len(grp_map)
    stats["modifiers"] = len(mod_to_group)
    station = db.query(models.KitchenStation).filter(models.KitchenStation.company_id == cid).first()
    prods = adapter.pull_products()
    attr_lines = [lid for p in prods for lid in (p.get("attribute_line_ids") or [])]
    attrs = adapter.pull_attribute_lines(attr_lines) if attr_lines and hasattr(adapter, "pull_attribute_lines") else {}
    images = {}
    if get_settings().odoo_import_images and hasattr(adapter, "pull_images") and prods:
        images = adapter.pull_images([p["id"] for p in prods])
    for p in prods:
        cat = cat_map.get(p["pos_category_id"][0]) if p.get("pos_category_id") else None
        groups = sorted({mod_to_group[m] for m in (p.get("pos_modifier_ids") or []) if m in mod_to_group})
        price = p.get("pos_price") or p.get("list_price") or 0
        obj = _upsert(db, models.Product, cid, str(p["id"]), name=(p.get("english_name") or p["name"])[:150],
                name_ur=(p["name"] if p.get("english_name") else "")[:150], sku=(p.get("default_code") or "")[:50],
                price=price, category_id=cat.id if cat else None,
                tax_id=None if p.get("is_vat_exempt") else (default_tax.id if default_tax else None),
                kitchen_station_id=station.id if station else None, modifier_group_ids=",".join(groups), active=True,
                attributes=attrs.get(p["id"], "")[:1000])
        if p["id"] in images:
            # Odoo image wins unless a manager uploaded one in Tezz admin
            if obj.image_source != "upload":
                obj.image_data = images[p["id"]]
                obj.image_source = "odoo"
    # Products no longer available in POS (or now excluded, e.g. 'Gift Card Product') are deactivated, not deleted.
    db.flush()
    keep = {str(p["id"]) for p in prods}
    removed = 0
    for obj in db.query(models.Product).filter(models.Product.company_id == cid, models.Product.erp_ref != "").all():
        if obj.erp_ref not in keep and obj.active:
            obj.active = False
            removed += 1
    stats["products"] = len(prods)
    stats["products_with_images"] = len(images)
    stats["products_with_attributes"] = len(attrs)
    stats["products_deactivated"] = removed
    custs = adapter.pull_customers()
    for c in custs:
        _upsert(db, models.Customer, cid, str(c["id"]), name=(c.get("name") or "")[:150], phone=(c.get("mobile") or "")[:30],
                ntn=(c.get("vat") or "")[:50] if c.get("vat") else "")
    stats["customers"] = len(custs)
    db.commit()
    stats["company_id"] = cid
    log.info("odoo import done: %s", {k: v for k, v in stats.items() if k != "company_id"})
    return stats
