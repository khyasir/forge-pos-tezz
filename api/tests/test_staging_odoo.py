"""Opt-in integration test against CS staging Odoo (never production).
Runs only with TEZZ_STAGING=1 and ERP_PROVIDER=odoo_wags env (inside the api container):
    docker compose exec -e TEZZ_STAGING=1 api python -m pytest tests/test_staging_odoo.py -q -p no:cacheprovider
Creates ONE draft quotation (sale.order.wags, state draft) labelled TEZZ-TEST with a
client_order_ref starting "TEZZ-TEST-SYNC-". Never confirms anything, never touches pos.wags/ZATCA.
The created id is printed so it can be cleaned up."""
import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(os.getenv("TEZZ_STAGING") != "1", reason="staging integration test is opt-in")


def test_push_twice_creates_one_draft_quotation():
    from app.adapters.erp.odoo_wags import OdooWagsAdapter

    a = OdooWagsAdapter()
    assert "staging" in a.url
    prod = a._x("product.product.wags", "search_read", [("available_in_pos", "=", True), ("active", "=", True),
                                                         ("is_modifier", "=", False)], fields=["id"], limit=1)[0]
    usin = f"TEZZ-TEST-SYNC-{uuid.uuid4().hex[:10]}"
    order = {"usin": usin, "order_no": "TEST-1", "order_type": "delivery", "delivery_fee": 150,
             "delivery_address": "Test address (automated sync test)",
             "lines": [{"name": "TEZZ TEST LINE", "qty": 1, "price": 1.0, "erp_product_ref": str(prod["id"])}]}
    r1 = a.push_order(order)
    r2 = a.push_order(order)  # retry/reconnect: must not create a second record
    assert r1.ok and r2.ok, (r1.error, r2.error)
    ids = a._x("sale.order.wags", "search", [("client_order_ref", "=", usin)])
    print(f"\nSTAGING_CREATED sale.order.wags ids={ids} client_order_ref={usin}")
    assert len(ids) == 1
    rec = a._x("sale.order.wags", "read", ids, fields=["state", "notes"])[0]
    assert rec["state"] == "draft" and "TEZZ-TEST" in (rec["notes"] or "")
