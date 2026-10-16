"""Adapter for WAGS-customised Odoo 16 (Camel Step). Uses XML-RPC execute_kw.

Safety rules (STAGING):
- Orders are pushed ONLY as sale.order.wags in state 'draft' (Quotation).
  We never call action_confirm / invoice / validate, and never touch pos.wags,
  which carries ZATCA signing fields. Nothing is sent to ZATCA.
- Idempotent on our USIN: client_order_ref == USIN; we search before create.
- Credentials come from env only (ODOO_PASSWORD or ODOO_API_KEY); never logged.
"""
from __future__ import annotations

import logging
import os
import xmlrpc.client

from ...config import get_settings
from .base import ERPAdapter, ERPPushResult

log = logging.getLogger("tezz.erp.odoo_wags")


class OdooWagsAdapter(ERPAdapter):
    ORDER_MODEL = "sale.order.wags"

    def __init__(self, url=None, db=None, username=None, secret=None, branch_id=None, transport=None):
        s = get_settings()
        self.url = (url or s.odoo_url).rstrip("/")
        self.db = db or s.odoo_db
        self.username = username or s.odoo_username
        self._secret = secret or s.odoo_password or s.odoo_api_key
        self.branch_id = branch_id if branch_id is not None else s.odoo_branch_id
        self.note_prefix = s.odoo_order_note_prefix
        self._transport = transport
        self._uid = None
        self._obj = None

    # --- low level -------------------------------------------------------
    def _proxy(self, path):
        return xmlrpc.client.ServerProxy(self.url + path, allow_none=True, transport=self._transport)

    def _x(self, model, method, *args, **kw):
        if not (self.url and self.db and self.username and self._secret):
            raise RuntimeError("Odoo is not configured (ODOO_URL/ODOO_DB/ODOO_USERNAME/ODOO_PASSWORD)")
        if "staging" not in self.url and os.getenv("ODOO_ALLOW_PRODUCTION") != "1":
            raise RuntimeError("Refusing non-staging Odoo URL (set ODOO_ALLOW_PRODUCTION=1 to override)")
        if self._uid is None:
            self._uid = self._proxy("/xmlrpc/2/common").authenticate(self.db, self.username, self._secret, {})
            if not self._uid:
                raise RuntimeError("Odoo authentication failed")
            self._obj = self._proxy("/xmlrpc/2/object")
        return self._obj.execute_kw(self.db, self._uid, self._secret, model, method, list(args), kw)

    def health(self) -> bool:
        try:
            self._x("res.company", "search_count", [])
            return True
        except Exception as exc:  # noqa: BLE001
            log.warning("odoo health failed: %s", type(exc).__name__)
            return False

    # --- pulls -----------------------------------------------------------
    def pull_categories(self):
        return self._x("pos.product.category.wags", "search_read", [("active", "=", True)],
                       fields=["name", "sort_order"], order="sort_order,id")

    def pull_taxes(self):
        return self._x("account.tax.wags", "search_read", [("type_tax_use", "=", "sale"), ("active", "=", True)],
                       fields=["name", "amount", "amount_type"])

    def pull_products(self, limit=None):
        limit = limit or get_settings().odoo_import_limit
        return self._x("product.product.wags", "search_read",
                       [("active", "=", True), ("available_in_pos", "=", True), ("is_modifier", "=", False),
                        ("is_gift_voucher", "=", False), ("name", "not ilike", "gift card")],
                       fields=["name", "english_name", "default_code", "barcode", "list_price", "pos_price",
                               "pos_category_id", "pos_modifier_ids", "is_vat_exempt", "attribute_line_ids",
                               "is_combo"], limit=limit, order="id")

    def pull_attribute_lines(self, line_ids):
        """Variant attributes per product (WAGS stores one product per variant,
        e.g. 'Zone: R'). Returned as {product_id: "Attr: Value; ..."}."""
        out = {}
        ids = list(line_ids)
        for i in range(0, len(ids), 200):
            rows = self._x("product.attribute.line.wags", "read", ids[i:i + 200],
                           fields=["product_id", "attribute_id", "value_id"])
            for r in rows:
                if not (r.get("product_id") and r.get("attribute_id") and r.get("value_id")):
                    continue
                out.setdefault(r["product_id"][0], []).append(f"{r['attribute_id'][1]}: {r['value_id'][1]}")
        return {k: "; ".join(v) for k, v in out.items()}

    def pull_images(self, product_ids, batch=20):
        """{product_id: data_url} for products that have an image."""
        out = {}
        ids = self._x("product.product.wags", "search", [("id", "in", list(product_ids)), ("image", "!=", False)])
        for i in range(0, len(ids), batch):
            for r in self._x("product.product.wags", "read", ids[i:i + batch], fields=["image"]):
                b64 = r.get("image")
                if not b64:
                    continue
                mime = "image/png" if b64.startswith("iVBOR") else "image/webp" if b64.startswith("UklGR") else \
                    "image/svg+xml" if b64.startswith("PHN2") or b64.startswith("PD94") else "image/jpeg"
                out[r["id"]] = f"data:{mime};base64,{b64}"
        return out

    def pull_modifiers(self):
        cats = self._x("pos.product.modifier.category.wags", "search_read", [], fields=["name"])
        mods = self._x("pos.product.modifier.wags", "search_read", [("active", "=", True)],
                       fields=["name", "price", "pos_product_modifier_category"])
        return cats, mods

    def pull_customers(self, limit=None):
        limit = limit or get_settings().odoo_customer_limit
        return self._x("res.partner", "search_read", [("customer_rank", ">", 0), ("mobile", "!=", False)]
                       if self._has_field("res.partner", "customer_rank") else [("mobile", "!=", False)],
                       fields=["name", "mobile", "vat"], limit=limit, order="id desc")

    def _has_field(self, model, field):
        try:
            return field in self._x(model, "fields_get", [field], attributes=["type"])
        except Exception:  # noqa: BLE001
            return False

    # --- push ------------------------------------------------------------
    def find_order(self, usin: str):
        ids = self._x(self.ORDER_MODEL, "search", [("client_order_ref", "=", usin)], limit=1)
        return ids[0] if ids else None

    def push_order(self, order: dict) -> ERPPushResult:
        usin = order.get("usin") or order.get("id")
        try:
            existing = self.find_order(usin)
            if existing:
                return ERPPushResult(ok=True, erp_ref=f"{self.ORDER_MODEL}:{existing}")
            lines = []
            skipped = []
            for ln in order.get("lines", []):
                ref = ln.get("erp_product_ref")
                if not ref:
                    skipped.append(ln.get("name", "?"))
                    continue
                lines.append((0, 0, {"product_id": int(ref), "quantity": ln["qty"], "price_unit": ln["price"],
                                     "name": ln.get("name", "")}))
            if not lines:
                return ERPPushResult(ok=False, error="No lines mapped to Odoo products (import products first)")
            note = f"{self.note_prefix} order from Tezz POS. USIN {usin}. Order {order.get('order_no','')}."
            if order.get("order_type"):
                note += f" Type: {order['order_type']}."
            if order.get("delivery_fee"):
                dp = get_settings().odoo_delivery_product_id
                if dp:
                    lines.append((0, 0, {"product_id": int(dp), "quantity": 1, "price_unit": order["delivery_fee"],
                                         "name": "Delivery Charges"}))
                note += f" Delivery charges: {order['delivery_fee']:.2f}."
                if order.get("delivery_address"):
                    note += f" Address: {order['delivery_address'][:200]}."
            if skipped:
                note += " Skipped unmapped lines: " + ", ".join(skipped)
            vals = {"client_order_ref": usin, "notes": note, "sale_type": "product",
                    "general_sale_type": "normal", "order_line": lines}
            if self.branch_id:
                vals["pos_branch_id"] = self.branch_id
            new_id = self._x(self.ORDER_MODEL, "create", [vals])
            new_id = new_id[0] if isinstance(new_id, list) else new_id
            st = self._x(self.ORDER_MODEL, "read", [new_id], fields=["state", "name"])[0]
            if st["state"] != "draft":
                return ERPPushResult(ok=False, erp_ref=f"{self.ORDER_MODEL}:{new_id}",
                                     error=f"Created but state is {st['state']} (expected draft)")
            return ERPPushResult(ok=True, erp_ref=f"{self.ORDER_MODEL}:{new_id}:{st['name']}")
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).splitlines()[-1][:300] if str(exc) else type(exc).__name__
            if self._secret and self._secret in msg:
                msg = msg.replace(self._secret, "***")
            return ERPPushResult(ok=False, error=f"Odoo push failed: {msg}")
