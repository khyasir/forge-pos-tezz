from .conftest import auth_headers


def _create_order(client, seeded, qty=2):
    headers = auth_headers(seeded)
    payload = {
        "client_uuid": "order-pay-1",
        "branch_id": seeded["branch_id"],
        "terminal_id": seeded["terminal_id"],
        "lines": [
            {
                "product_id": seeded["product_id"],
                "name_snapshot": "Burger",
                "qty": qty,
                "unit_price": 500,
                "modifiers": [],
            }
        ],
    }
    r = client.post("/api/v1/orders", json=payload, headers=headers)
    assert r.status_code == 201
    return r.json()


def test_pay_order_cash_applies_tax_fee_and_fiscalizes(client, seeded):
    headers = auth_headers(seeded)
    order = _create_order(client, seeded, qty=2)
    assert order["subtotal"] == 1000

    r = client.post(
        f"/api/v1/orders/{order['id']}/pay",
        json={"payments": [{"payment_method_id": seeded["cash_pm"], "amount": 1000, "tendered": 1200}]},
        headers=headers,
    )
    assert r.status_code == 200
    paid = r.json()
    assert paid["status"] == "paid"
    assert paid["payment_mode"] == "cash"
    assert paid["tax_amount"] == 160  # 16% cash rate on 1000
    assert paid["pos_fee"] == 1.0
    assert paid["total"] == 1161.0
    assert paid["fiscal_status"] == "ok"
    assert paid["fiscal_number"]
    assert paid["erp_status"] == "ok"


def test_pay_order_card_uses_card_rate(client, seeded):
    headers = auth_headers(seeded)
    order = _create_order(client, seeded, qty=1)
    r = client.post(
        f"/api/v1/orders/{order['id']}/pay",
        json={"payments": [{"payment_method_id": seeded["card_pm"], "amount": 500, "tendered": 500}]},
        headers=headers,
    )
    paid = r.json()
    assert paid["tax_amount"] == 25  # 5% card rate on 500


def test_cannot_pay_twice(client, seeded):
    headers = auth_headers(seeded)
    order = _create_order(client, seeded, qty=1)
    pay_body = {"payments": [{"payment_method_id": seeded["cash_pm"], "amount": 500, "tendered": 500}]}
    r1 = client.post(f"/api/v1/orders/{order['id']}/pay", json=pay_body, headers=headers)
    assert r1.status_code == 200
    r2 = client.post(f"/api/v1/orders/{order['id']}/pay", json=pay_body, headers=headers)
    assert r2.status_code == 400


def test_void_and_refund(client, seeded):
    headers = auth_headers(seeded)
    order = _create_order(client, seeded, qty=1)

    r = client.post(f"/api/v1/orders/{order['id']}/void", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "void"

    import uuid

    order2_payload = {
        "client_uuid": uuid.uuid4().hex,
        "branch_id": seeded["branch_id"],
        "lines": [{"product_id": seeded["product_id"], "name_snapshot": "Burger", "qty": 1, "unit_price": 500}],
    }
    order2 = client.post("/api/v1/orders", json=order2_payload, headers=headers).json()
    client.post(
        f"/api/v1/orders/{order2['id']}/pay",
        json={"payments": [{"payment_method_id": seeded["cash_pm"], "amount": 500, "tendered": 500}]},
        headers=headers,
    )
    r = client.post(f"/api/v1/orders/{order2['id']}/refund", json={"reason": "customer changed mind"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "refunded"


def test_offline_order_marked_pending_fiscal(client, seeded):
    headers = auth_headers(seeded)
    import uuid

    payload = {
        "client_uuid": uuid.uuid4().hex,
        "branch_id": seeded["branch_id"],
        "offline": True,
        "lines": [{"product_id": seeded["product_id"], "name_snapshot": "Burger", "qty": 1, "unit_price": 500}],
    }
    order = client.post("/api/v1/orders", json=payload, headers=headers).json()
    r = client.post(
        f"/api/v1/orders/{order['id']}/pay",
        json={"payments": [{"payment_method_id": seeded["cash_pm"], "amount": 500, "tendered": 500}]},
        headers=headers,
    )
    # v2: an order rung up offline is fiscalized as soon as it reaches the server.
    assert r.json()["fiscal_status"] == "ok"
    assert r.json()["offline"] is True


def test_fiscal_retry_after_coming_online(client, seeded):
    headers = auth_headers(seeded)
    import uuid

    payload = {
        "client_uuid": uuid.uuid4().hex,
        "branch_id": seeded["branch_id"],
        "offline": True,
        "lines": [{"product_id": seeded["product_id"], "name_snapshot": "Burger", "qty": 1, "unit_price": 500}],
    }
    order = client.post("/api/v1/orders", json=payload, headers=headers).json()
    client.post(
        f"/api/v1/orders/{order['id']}/pay",
        json={"payments": [{"payment_method_id": seeded["cash_pm"], "amount": 500, "tendered": 500}]},
        headers=headers,
    )
    r = client.post(f"/api/v1/fiscal/{order['id']}/retry", headers=headers)
    assert r.status_code == 200
    assert r.json()["fiscal_status"] == "ok"
