"""Offline tests for the WAGS Odoo adapter using a fake XML-RPC backend."""
from app.adapters.erp.odoo_wags import OdooWagsAdapter


class FakeOdoo:
    def __init__(self):
        self.orders = {}
        self.calls = []

    def __call__(self, model, method, *args, **kw):
        self.calls.append((model, method))
        if model == "sale.order.wags" and method == "search":
            ref = args[0][0][2]
            return [i for i, o in self.orders.items() if o["client_order_ref"] == ref][:1]
        if model == "sale.order.wags" and method == "create":
            i = len(self.orders) + 1
            self.orders[i] = dict(args[0][0], state="draft", name=f"SO{i}")
            return i
        if model == "sale.order.wags" and method == "read":
            o = self.orders[args[0][0]]
            return [{"state": o["state"], "name": o["name"]}]
        raise AssertionError(f"unexpected call {model}.{method}")


def make():
    a = OdooWagsAdapter(url="https://x", db="d", username="u", secret="sekret-xyz", branch_id=24)
    fake = FakeOdoo()
    a._x = fake
    return a, fake


ORDER = {"usin": "U-1", "order_no": "G-1", "lines": [{"name": "Tea", "qty": 2, "price": 5.0, "erp_product_ref": "77"}]}


def test_push_creates_draft_quotation_once():
    a, fake = make()
    r1 = a.push_order(ORDER)
    r2 = a.push_order(ORDER)
    assert r1.ok and r2.ok and len(fake.orders) == 1
    o = fake.orders[1]
    assert o["client_order_ref"] == "U-1" and o["pos_branch_id"] == 24 and "TEZZ-TEST" in o["notes"]
    assert o["order_line"][0][2]["product_id"] == 77
    # never confirms/validates or touches ZATCA-bearing pos.wags
    assert not any(m in ("action_confirm", "action_invoice", "validate") or mo == "pos.wags" for mo, m in fake.calls)


def test_push_without_mapped_lines_fails_without_writes():
    a, fake = make()
    r = a.push_order({"usin": "U-2", "lines": [{"name": "X", "qty": 1, "price": 1, "erp_product_ref": ""}]})
    assert not r.ok and not fake.orders


def test_missing_config_reports_error(monkeypatch):
    for k in ("ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_PASSWORD", "ODOO_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    from app.config import get_settings
    s = get_settings()
    for f in ("odoo_url", "odoo_db", "odoo_username", "odoo_password", "odoo_api_key"):
        monkeypatch.setattr(s, f, "")
    a = OdooWagsAdapter(url="", db="", username="", secret="")
    r = a.push_order(ORDER)
    assert not r.ok and "not configured" in r.error


def test_refuses_non_staging_url(monkeypatch):
    monkeypatch.delenv("ODOO_ALLOW_PRODUCTION", raising=False)
    a = OdooWagsAdapter(url="https://erp.example.com", db="d", username="u", secret="sekret-xyz")
    r = a.push_order(ORDER)
    assert not r.ok and "non-staging" in r.error
