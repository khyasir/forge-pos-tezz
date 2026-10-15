from app import models

from .conftest import auth_headers


def _order_payload(seeded, client_uuid, qty=1):
    return {
        "client_uuid": client_uuid,
        "branch_id": seeded["branch_id"],
        "terminal_id": seeded["terminal_id"],
        "order_type": "takeaway",
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


def test_sync_batch_idempotent_upsert(client, seeded):
    headers = auth_headers(seeded)
    body = {
        "terminal_id": seeded["terminal_id"],
        "orders": [_order_payload(seeded, "client-uuid-1")],
    }
    r1 = client.post("/api/v1/sync/batch", json=body, headers=headers)
    assert r1.status_code == 200
    server_id_1 = r1.json()["results"][0]["server_id"]

    # Resend the same batch (as the offline client would on reconnect) --
    # must not create a duplicate order.
    r2 = client.post("/api/v1/sync/batch", json=body, headers=headers)
    assert r2.status_code == 200
    server_id_2 = r2.json()["results"][0]["server_id"]
    assert server_id_1 == server_id_2

    r = client.get("/api/v1/orders", headers=headers)
    matching = [o for o in r.json() if o["client_uuid"] == "client-uuid-1"]
    assert len(matching) == 1


def test_sync_status_counts(client, seeded):
    headers = auth_headers(seeded)
    body = {
        "terminal_id": seeded["terminal_id"],
        "orders": [_order_payload(seeded, "client-uuid-a"), _order_payload(seeded, "client-uuid-b")],
    }
    client.post("/api/v1/sync/batch", json=body, headers=headers)

    r = client.get("/api/v1/sync/status", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["pending"] >= 2
    assert len(data["orders"]) >= 2


def test_sync_status_reports_fiscal_failure_reason(client, seeded, db_session):
    headers = auth_headers(seeded)
    body = {
        "terminal_id": seeded["terminal_id"],
        "orders": [_order_payload(seeded, "client-uuid-failed")],
    }
    r = client.post("/api/v1/sync/batch", json=body, headers=headers)
    server_id = r.json()["results"][0]["server_id"]

    order = db_session.query(models.Order).filter(models.Order.id == server_id).first()
    order.fiscal_status = "failed"
    order.fiscal_error = "FBR gateway timeout"
    db_session.commit()

    status = client.get("/api/v1/sync/status", headers=headers).json()
    row = next(o for o in status["orders"] if o["order_id"] == server_id)
    assert row["status"] == "failed"
    assert row["fiscal_error"] == "FBR gateway timeout"


def test_demo_unsynced_orders_endpoint(client):
    r = client.get("/api/v1/demo/unsynced-orders")
    assert r.status_code == 200
    assert r.json() == []
