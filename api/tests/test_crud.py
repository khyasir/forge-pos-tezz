from .conftest import auth_headers


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_category_crud(client, seeded):
    headers = auth_headers(seeded)
    r = client.post("/api/v1/categories", json={"company_id": "ignored", "name": "Drinks"}, headers=headers)
    assert r.status_code == 201
    cat = r.json()
    assert cat["name"] == "Drinks"
    assert cat["company_id"] == seeded["company_id"]

    r = client.get("/api/v1/categories", headers=headers)
    assert r.status_code == 200
    assert any(c["id"] == cat["id"] for c in r.json())

    r = client.patch(f"/api/v1/categories/{cat['id']}", json={"name": "Beverages"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Beverages"

    r = client.delete(f"/api/v1/categories/{cat['id']}", headers=headers)
    assert r.status_code == 204

    r = client.get(f"/api/v1/categories/{cat['id']}", headers=headers)
    assert r.status_code == 404


def test_crud_requires_auth(client, seeded):
    r = client.get("/api/v1/categories")
    assert r.status_code == 401


def test_crud_is_company_scoped(client, seeded, db_session):
    from app import models

    other = models.Company(id="co2", name="Other Co")
    other_cat = models.Category(id="catX", company_id="co2", name="Hidden")
    db_session.add_all([other, other_cat])
    db_session.commit()

    headers = auth_headers(seeded)
    r = client.get("/api/v1/categories", headers=headers)
    assert all(c["id"] != "catX" for c in r.json())
    r = client.get("/api/v1/categories/catX", headers=headers)
    assert r.status_code == 404


def test_product_and_modifier_group_crud(client, seeded):
    headers = auth_headers(seeded)
    r = client.post(
        "/api/v1/modifier-groups",
        json={"company_id": "x", "name": "Spice", "min_select": 0, "max_select": 1},
        headers=headers,
    )
    assert r.status_code == 201
    group_id = r.json()["id"]

    r = client.post(
        "/api/v1/modifiers",
        json={"group_id": group_id, "name": "Hot", "price_delta": 0},
        headers=headers,
    )
    assert r.status_code == 201

    r = client.get("/api/v1/modifier-groups", headers=headers)
    assert r.status_code == 200
    assert any(g["id"] == group_id for g in r.json())
