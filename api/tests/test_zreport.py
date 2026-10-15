import uuid

from .conftest import auth_headers


def _pay(client, seeded, headers, shift_id, amount_qty=1):
    payload = {
        "client_uuid": uuid.uuid4().hex,
        "branch_id": seeded["branch_id"],
        "terminal_id": seeded["terminal_id"],
        "shift_id": shift_id,
        "lines": [
            {
                "product_id": seeded["product_id"],
                "name_snapshot": "Burger",
                "qty": amount_qty,
                "unit_price": 500,
            }
        ],
    }
    order = client.post("/api/v1/orders", json=payload, headers=headers).json()
    subtotal = 500 * amount_qty
    total = round(subtotal + subtotal * 0.16 + 1.0, 2)  # cash rate 16% + Rs.1 POS fee
    client.post(
        f"/api/v1/orders/{order['id']}/pay",
        json={"payments": [{"payment_method_id": seeded["cash_pm"], "amount": total, "tendered": total}]},
        headers=headers,
    )
    return order


def test_open_close_shift_and_z_report(client, seeded):
    headers = auth_headers(seeded)
    r = client.post(
        "/api/v1/shifts",
        json={"branch_id": seeded["branch_id"], "terminal_id": seeded["terminal_id"], "user_id": "u1", "opening_float": 2000},
        headers=headers,
    )
    assert r.status_code == 201
    shift = r.json()
    assert shift["status"] == "open"

    _pay(client, seeded, headers, shift["id"], amount_qty=2)
    _pay(client, seeded, headers, shift["id"], amount_qty=1)

    expected_cash = 2000 + 1161.0 + 581.0  # opening float + two cash totals (16% tax + Rs.1 fee)
    r = client.post(f"/api/v1/shifts/{shift['id']}/close", json={"counted_cash": 3576.0}, headers=headers)
    assert r.status_code == 200
    closed = r.json()
    assert closed["status"] == "closed"
    assert closed["expected_cash"] == expected_cash
    assert closed["over_short"] == round(3576.0 - expected_cash, 2)

    r = client.get(f"/api/v1/shifts/{shift['id']}/z-report", headers=headers)
    assert r.status_code == 200
    report = r.json()
    assert report["order_count"] == 2
    assert report["gross_sales"] == 1500
    assert report["by_payment_method"]["Cash"] == 1742.0


def test_cannot_open_two_shifts_on_same_terminal(client, seeded):
    headers = auth_headers(seeded)
    body = {"branch_id": seeded["branch_id"], "terminal_id": seeded["terminal_id"], "user_id": "u1", "opening_float": 1000}
    r1 = client.post("/api/v1/shifts", json=body, headers=headers)
    assert r1.status_code == 201
    r2 = client.post("/api/v1/shifts", json=body, headers=headers)
    assert r2.status_code == 400
