import itertools

import httpx

from ...config import get_settings
from .base import ERPAdapter, ERPPushResult

settings = get_settings()
_id_counter = itertools.count(1)


class OdooJSONRPCError(Exception):
    pass


class OdooAdapter(ERPAdapter):
    """Odoo 16 adapter skeleton using JSON-RPC (`/jsonrpc`) execute_kw.

    Unused unless ERP_PROVIDER=odoo. Reads product.product and pushes orders
    via pos.order's create_from_ui. Not exercised in tests (no live Odoo
    instance in CI) -- see docs-POS_PLAN.md section 6 for the full design
    (pos.session handling, tax/payment-method mapping).
    """

    def __init__(self) -> None:
        self.url = settings.odoo_url.rstrip("/")
        self.db = settings.odoo_db
        self.username = settings.odoo_username
        self.api_key = settings.odoo_api_key
        self._uid: int | None = None

    def _call(self, service: str, method: str, args: list):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"service": service, "method": method, "args": args},
            "id": next(_id_counter),
        }
        resp = httpx.post(f"{self.url}/jsonrpc", json=payload, timeout=15.0)
        data = resp.json()
        if "error" in data:
            raise OdooJSONRPCError(data["error"].get("data", {}).get("message", str(data["error"])))
        return data["result"]

    def _authenticate(self) -> int:
        if self._uid is None:
            self._uid = self._call("common", "login", [self.db, self.username, self.api_key])
        return self._uid

    def _execute_kw(self, model: str, method: str, args: list, kwargs: dict | None = None):
        uid = self._authenticate()
        call_args = [self.db, uid, self.api_key, model, method, args]
        if kwargs:
            call_args.append(kwargs)
        return self._call("object", "execute_kw", call_args)

    def pull_products(self) -> list[dict]:
        return self._execute_kw(
            "product.product",
            "search_read",
            [[["available_in_pos", "=", True]]],
            {"fields": ["id", "name", "list_price", "taxes_id", "barcode", "pos_categ_id"]},
        )

    def pull_customers(self) -> list[dict]:
        return self._execute_kw("res.partner", "search_read", [[]], {"fields": ["id", "name", "phone", "vat"]})

    def push_order(self, order: dict) -> ERPPushResult:
        try:
            order_ref = self._execute_kw("pos.order", "create_from_ui", [[order]])
            return ERPPushResult(ok=True, erp_ref=str(order_ref))
        except OdooJSONRPCError as exc:
            return ERPPushResult(ok=False, error=str(exc))

    def health(self) -> bool:
        try:
            self._call("common", "version", [])
            return True
        except (OdooJSONRPCError, httpx.HTTPError):
            return False
