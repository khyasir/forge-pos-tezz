import uuid

from .conftest import auth_headers


def _paid_order(client, seeded):
    headers = auth_headers(seeded)
    payload = {
        "client_uuid": uuid.uuid4().hex,
        "branch_id": seeded["branch_id"],
        "customer_id": None,
        "lines": [
            {
                "product_id": seeded["product_id"],
                "name_snapshot": "Burger",
                "qty": 1,
                "unit_price": 500,
                "modifiers": [{"name_snapshot": "Extra Cheese", "price_delta": 150}],
            }
        ],
    }
    order = client.post("/api/v1/orders", json=payload, headers=headers).json()
    client.post(
        f"/api/v1/orders/{order['id']}/pay",
        json={
            "payments": [{"payment_method_id": seeded["cash_pm"], "amount": 500, "tendered": 1000}],
            "customer_phone": "03001234567",
        },
        headers=headers,
    )
    return client.get(f"/api/v1/orders/{order['id']}", headers=headers).json()


def test_receipt_json_has_sro_1006_fields(client, seeded):
    order = _paid_order(client, seeded)
    assert order["fiscal_number"]
    assert order["tax_amount"] > 0
    assert order["pos_fee"] == 1.0
    assert order["total"] > order["subtotal"]


def test_receipt_html_renders_with_qr_and_fiscal_number(client, seeded):
    headers = auth_headers(seeded)
    order = _paid_order(client, seeded)
    r = client.get(f"/api/v1/orders/{order['id']}/receipt.html", headers=headers)
    assert r.status_code == 200
    html = r.text
    assert order["fiscal_number"] in html
    assert "<svg" in html
    assert "Verify this invoice through FBR Tax Asaan" in html
    assert "POS Service Fee" in html
    assert "NTN:" in html and "STRN:" in html


def test_receipt_html_offline_mode_label(client, seeded):
    headers = auth_headers(seeded)
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
    r = client.get(f"/api/v1/orders/{order['id']}/receipt.html", headers=headers)
    assert "OFFLINE MODE" in r.text
