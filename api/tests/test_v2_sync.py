"""v2: delivery charges, product images, company isolation, idempotency,
automatic retry with backoff, crash recovery, Odoo import mapping."""
import base64
import threading
import uuid
from datetime import datetime, timedelta

import pytest

from app import models
from app.adapters.erp.base import ERPPushResult
from app.adapters.fiscal.base import FiscalResult
from app.services import orders as svc
from app.services.erp_import import run_import
from tests.conftest import auth_headers

PNG = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 20).decode()


class CountingFiscal:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def fiscalize(self, invoice):
        self.calls.append(invoice)
        if self.fail:
            return FiscalResult(ok=False, error="FBR gateway timeout")
        return FiscalResult(ok=True, fiscal_number=f"FN-{len(self.calls)}", qr_payload="qr")


class CountingERP:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def push_order(self, payload):
        self.calls.append(payload)
        if self.fail:
            return ERPPushResult(ok=False, error="Odoo down")
        return ERPPushResult(ok=True, erp_ref="sale.order.wags:1")


@pytest.fixture()
def adapters(monkeypatch):
    f, e = CountingFiscal(), CountingERP()
    monkeypatch.setattr(svc, "get_fiscal_adapter", lambda: f)
    monkeypatch.setattr(svc, "get_erp_adapter", lambda: e)
    # make the line look ERP-linked so the real adapter (our fake) is used
    return f, e


def _order(seeded, **extra):
    body = {
        "client_uuid": uuid.uuid4().hex,
        "branch_id": seeded["branch_id"],
        "lines": [{"product_id": seeded["product_id"], "name_snapshot": "Burger", "qty": 1, "unit_price": 500}],
    }
    body.update(extra)
    return body


def _pay(client, seeded, oid, pm="cash_pm", amount=1000):
    return client.post(
        f"/api/v1/orders/{oid}/pay",
        json={"payments": [{"payment_method_id": seeded[pm], "amount": amount, "tendered": amount}]},
        headers=auth_headers(seeded),
    )


# ---------------- delivery ----------------
def test_delivery_fee_default_and_tax(client, seeded):
    h = auth_headers(seeded)
    o = client.post("/api/v1/orders", json=_order(seeded, order_type="delivery", delivery_address="House 5, DHA"), headers=h).json()
    assert o["delivery_fee"] == 150  # company default
    paid = _pay(client, seeded, o["id"]).json()
    # PRA cash rate 16% on (500 + 150) = 104 ; total = 500 + 150 + 104 + 1 POS fee
    assert paid["tax_amount"] == 104
    assert paid["total"] == 755
    html = client.get(f"/api/v1/orders/{o['id']}/receipt.html", headers=h).text
    assert "Delivery Charges" in html and "House 5, DHA" in html


def test_delivery_fee_explicit_and_not_for_dine_in(client, seeded):
    h = auth_headers(seeded)
    o = client.post("/api/v1/orders", json=_order(seeded, order_type="delivery", delivery_fee=99), headers=h).json()
    assert o["delivery_fee"] == 99
    o2 = client.post("/api/v1/orders", json=_order(seeded, order_type="dine_in", delivery_fee=99), headers=h).json()
    assert o2["delivery_fee"] == 0


def test_delivery_in_fbr_and_erp_payload(client, seeded, db_session):
    o = client.post("/api/v1/orders", json=_order(seeded, order_type="delivery", delivery_fee=200), headers=auth_headers(seeded)).json()
    order = db_session.get(models.Order, o["id"])
    inv = svc._build_fiscal_invoice(db_session, order, True)
    item = [i for i in inv["Items"] if i["ItemCode"] == "DELIVERY"][0]
    assert item["SaleValue"] == 200 and item["TaxCharged"] == 32
    assert inv["TotalSaleValue"] == 700
    erp = svc.build_erp_payload(db_session, order)
    assert erp["delivery_fee"] == 200 and erp["order_type"] == "delivery"


def test_odoo_push_adds_delivery_note():
    from app.adapters.erp.odoo_wags import OdooWagsAdapter
    from tests.test_odoo_wags import FakeOdoo

    a = OdooWagsAdapter(url="https://x", db="d", username="u", secret="s", branch_id=24)
    fake = FakeOdoo()
    a._x = fake
    a.push_order({"usin": "U-D", "order_type": "delivery", "delivery_fee": 150, "delivery_address": "Gulberg",
                  "lines": [{"name": "Tea", "qty": 1, "price": 5, "erp_product_ref": "7"}]})
    assert "Delivery charges: 150.00" in fake.orders[1]["notes"] and "Gulberg" in fake.orders[1]["notes"]


def test_company_default_delivery_fee_editable(client, seeded):
    h = auth_headers(seeded)
    r = client.patch(f"/api/v1/companies/{seeded['company_id']}", json={"default_delivery_fee": 250}, headers=h)
    assert r.status_code == 200 and r.json()["default_delivery_fee"] == 250


# ---------------- images ----------------
def test_product_image_upload_serve_delete(client, seeded):
    h = auth_headers(seeded)
    pid = seeded["product_id"]
    assert client.get(f"/api/v1/products/{pid}", headers=h).json()["image_url"] == ""
    r = client.put(f"/api/v1/products/{pid}/image", json={"data_url": PNG}, headers=h)
    assert r.status_code == 200 and r.json()["image_url"].startswith(f"/api/v1/products/{pid}/image")
    img = client.get(f"/api/v1/products/{pid}/image")
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"
    assert client.put(f"/api/v1/products/{pid}/image", json={"data_url": "hello"}, headers=h).status_code == 400
    client.delete(f"/api/v1/products/{pid}/image", headers=h)
    assert client.get(f"/api/v1/products/{pid}/image").status_code == 404


# ---------------- isolation ----------------
@pytest.fixture()
def other_company(db_session):
    from app.security import generate_api_key

    db_session.add_all([
        models.Company(id="co2", name="Other"),
        models.Branch(id="br2", company_id="co2", name="Other main"),
        models.Terminal(id="t2", branch_id="br2", name="T2"),
        models.ModifierGroup(id="mg2", company_id="co2", name="Secret"),
        models.Modifier(id="m2", group_id="mg2", name="Secret mod"),
    ])
    key = models.ApiKey(id="k2", company_id="co2", key=generate_api_key())
    db_session.add(key)
    db_session.commit()
    return {"Authorization": f"Bearer {key.key}"}


def test_company_isolation(client, seeded, other_company):
    h = auth_headers(seeded)
    assert [c["id"] for c in client.get("/api/v1/companies", headers=h).json()] == ["co1"]
    assert client.get("/api/v1/companies/co2", headers=h).status_code == 404
    assert client.patch("/api/v1/companies/co2", json={"name": "x"}, headers=h).status_code == 404
    assert "t2" not in [t["id"] for t in client.get("/api/v1/terminals", headers=h).json()]
    assert client.get("/api/v1/modifiers/m2", headers=h).status_code == 404
    assert client.post("/api/v1/modifiers", json={"group_id": "mg2", "name": "x"}, headers=h).status_code == 404
    # order on another company's branch is rejected
    assert client.post("/api/v1/orders", json=_order(seeded, branch_id="br2"), headers=h).status_code == 400
    # the same client_uuid can't be used to read another company's order
    body = _order(seeded)
    client.post("/api/v1/orders", json=body, headers=h)
    r = client.post("/api/v1/sync/batch", json={"terminal_id": "t2", "orders": [dict(body, branch_id="br2")]}, headers=other_company)
    assert r.json()["results"][0]["status"] == "rejected"


# ---------------- idempotency ----------------
def test_double_submit_same_uuid_creates_one_order(client, seeded):
    h = auth_headers(seeded)
    body = _order(seeded)
    a = client.post("/api/v1/orders", json=body, headers=h).json()
    b = client.post("/api/v1/orders", json=body, headers=h).json()
    s = client.post("/api/v1/sync/batch", json={"terminal_id": "t1", "orders": [body, body]}, headers=h).json()
    assert a["id"] == b["id"] == s["results"][0]["server_id"] == s["results"][1]["server_id"]


def test_double_pay_charges_and_fiscalizes_once(client, seeded, adapters, db_session):
    f, e = adapters
    db_session.get(models.Product, seeded["product_id"]).erp_ref = "77"
    db_session.commit()
    o = client.post("/api/v1/orders", json=_order(seeded), headers=auth_headers(seeded)).json()
    assert _pay(client, seeded, o["id"]).status_code == 200
    assert _pay(client, seeded, o["id"]).status_code == 400
    assert len(f.calls) == 1 and len(e.calls) == 1
    assert db_session.query(models.Payment).filter_by(order_id=o["id"]).count() == 1


def test_claim_blocks_concurrent_sender(client, seeded, adapters, db_session):
    f, _ = adapters
    o = client.post("/api/v1/orders", json=_order(seeded), headers=auth_headers(seeded)).json()
    order = db_session.get(models.Order, o["id"])
    order.status, order.payment_mode, order.fiscal_status = "paid", "cash", "sending"  # another worker holds it
    db_session.commit()
    svc.run_fiscal(db_session, order)
    assert f.calls == []  # did not send a duplicate invoice
    order.fiscal_status = "ok"
    db_session.commit()
    svc.run_fiscal(db_session, order)
    assert f.calls == []  # already ok -> never resent


def test_parallel_pay_threads_only_one_wins(seeded, db_session, monkeypatch):
    """Two cashiers/tabs press Pay at the same instant."""
    f, e = CountingFiscal(), CountingERP()
    monkeypatch.setattr(svc, "get_fiscal_adapter", lambda: f)
    monkeypatch.setattr(svc, "get_erp_adapter", lambda: e)
    from app import schemas
    from tests.conftest import TestSessionLocal

    order, _ = svc.get_or_create_order(db_session, "co1", schemas.OrderCreate(**_order(seeded)))
    results, lock = [], threading.Lock()

    def worker():
        s = TestSessionLocal()
        try:
            o = s.get(models.Order, order.id)
            svc.pay_order(s, o, [schemas.PaymentIn(payment_method_id="pm_cash", amount=600, tendered=600)], None)
            with lock:
                results.append("ok")
        except ValueError:
            with lock:
                results.append("rejected")
        finally:
            s.close()

    ts = [threading.Thread(target=worker) for _ in range(2)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(results) == ["ok", "rejected"]
    assert len(f.calls) == 1


# ---------------- automatic retry ----------------
def test_auto_retry_with_backoff_then_success(client, seeded, db_session, monkeypatch):
    f = CountingFiscal(fail=True)
    monkeypatch.setattr(svc, "get_fiscal_adapter", lambda: f)
    o = client.post("/api/v1/orders", json=_order(seeded), headers=auth_headers(seeded)).json()
    paid = _pay(client, seeded, o["id"]).json()
    assert paid["fiscal_status"] == "failed"
    order = db_session.get(models.Order, o["id"])
    db_session.refresh(order)
    first_due = order.next_retry_at
    assert first_due > datetime.utcnow() + timedelta(seconds=20)

    # not due yet -> nothing sent
    svc.retry_due_orders(db_session)
    assert len(f.calls) == 1
    # due -> retried, still failing -> backoff grows
    svc.retry_due_orders(db_session, now=first_due + timedelta(seconds=1))
    db_session.refresh(order)
    assert len(f.calls) == 2 and order.next_retry_at - datetime.utcnow() > timedelta(seconds=50)
    # FBR back -> succeeds, then never sent again
    f.fail = False
    svc.retry_due_orders(db_session, now=order.next_retry_at + timedelta(seconds=1))
    db_session.refresh(order)
    assert order.fiscal_status == "ok" and len(f.calls) == 3
    svc.retry_due_orders(db_session, now=datetime.utcnow() + timedelta(days=1))
    assert len(f.calls) == 3


def test_crash_mid_send_is_recovered(client, seeded, db_session, adapters):
    f, _ = adapters
    o = client.post("/api/v1/orders", json=_order(seeded), headers=auth_headers(seeded)).json()
    order = db_session.get(models.Order, o["id"])
    order.status, order.payment_mode = "paid", "cash"
    order.fiscal_status = "sending"  # process died while talking to FBR
    order.updated_at = datetime.utcnow() - timedelta(minutes=10)
    db_session.commit()
    svc.retry_due_orders(db_session)
    db_session.refresh(order)
    assert order.fiscal_status == "ok" and len(f.calls) == 1


def test_offline_order_is_fiscalized_on_sync(client, seeded, adapters):
    f, _ = adapters
    body = _order(seeded, offline=True, created_at=(datetime.utcnow() - timedelta(hours=2)).isoformat())
    s = client.post("/api/v1/sync/batch", json={"terminal_id": "t1", "orders": [body]}, headers=auth_headers(seeded)).json()
    paid = _pay(client, seeded, s["results"][0]["server_id"]).json()
    assert paid["offline"] is True and paid["fiscal_status"] == "ok" and len(f.calls) == 1


# ---------------- Odoo import mapping ----------------
class FakeImportAdapter:
    def pull_taxes(self):
        return [{"id": 1, "name": "VAT 15%", "amount": 15, "amount_type": "percent"}]

    def pull_categories(self):
        return [{"id": 5, "name": "Shoes", "sort_order": 1}]

    def pull_modifiers(self):
        return [{"id": 9, "name": "Extras"}], [{"id": 90, "name": "Gift box", "price": 10, "pos_product_modifier_category": [9, "Extras"]}]

    def pull_products(self):
        return [
            {"id": 100, "name": "Sandal", "english_name": "", "default_code": "S1", "pos_price": 50, "list_price": 50,
             "pos_category_id": [5, "Shoes"], "pos_modifier_ids": [90], "is_vat_exempt": False, "attribute_line_ids": [7]},
            {"id": 101, "name": "Boot", "pos_price": 80, "pos_category_id": False, "pos_modifier_ids": [], "attribute_line_ids": []},
        ]

    def pull_attribute_lines(self, ids):
        return {100: "Size: 42"}

    def pull_images(self, ids):
        return {100: PNG}

    def pull_customers(self):
        return []


def test_odoo_import_maps_images_attributes_modifiers(db_session):
    stats = run_import(db_session, FakeImportAdapter())
    p = db_session.query(models.Product).filter_by(erp_ref="100").one()
    assert p.attributes == "Size: 42" and p.image_source == "odoo" and p.modifier_group_ids
    assert stats["products_with_images"] == 1
    # an image uploaded in Tezz admin is not overwritten by a re-import
    p.image_source, p.image_data = "upload", PNG + "AA"
    db_session.commit()
    run_import(db_session, FakeImportAdapter())
    db_session.refresh(p)
    assert p.image_source == "upload"


def test_odoo_import_deactivates_removed_products(db_session):
    a = FakeImportAdapter()
    run_import(db_session, a)
    a.pull_products = lambda: FakeImportAdapter().pull_products()[:1]
    stats = run_import(db_session, a)
    assert stats["products_deactivated"] == 1
    assert db_session.query(models.Product).filter_by(erp_ref="101").one().active is False


def test_gift_card_excluded_in_odoo_domain():
    from app.adapters.erp.odoo_wags import OdooWagsAdapter

    a = OdooWagsAdapter(url="https://x", db="d", username="u", secret="s")
    seen = {}

    def fake(model, method, *args, **kw):
        seen["domain"] = args[0]
        return []

    a._x = fake
    a.pull_products()
    assert ("name", "not ilike", "gift card") in seen["domain"]
    assert ("available_in_pos", "=", True) in seen["domain"]


def test_blank_or_stale_refs_do_not_block_sync(client, seeded):
    """Regression: a cashier logged in without a terminal went offline; the
    batch carried terminal_id="" and the whole batch failed with a 500."""
    h = auth_headers(seeded)
    good = _order(seeded)
    bad = _order(seeded, terminal_id="", user_id="ghost", table_id="gone", customer_id="")
    r = client.post("/api/v1/sync/batch", json={"terminal_id": "", "orders": [bad, good]}, headers=h)
    assert r.status_code == 200
    res = r.json()["results"]
    assert [x["status"] for x in res] == ["open", "open"]
