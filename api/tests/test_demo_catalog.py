"""Regression: the cashier screen must always get the demo catalog after a
fresh start or an upgrade, and a login from a previous (reset) database must
be rejected with 401 so the web app sends the cashier back to the PIN screen
instead of showing an empty product grid."""
from sqlalchemy import create_engine, inspect, text

from app import models
from app.database import Base, add_missing_columns
from app.seed import DEMO_API_KEY, run_seed


def _login(client, branch_id, terminal_id=None, pin="3333"):
    body = {"branch_id": branch_id, "pin": pin}
    if terminal_id:
        body["terminal_id"] = terminal_id
    r = client.post("/api/v1/auth/login", json=body)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_cashier_sees_demo_products_for_every_branch_and_terminal(db_session, client):
    run_seed(db_session)
    demo = {"Authorization": f"Bearer {DEMO_API_KEY}"}
    branches = client.get("/api/v1/branches?limit=100", headers=demo).json()
    terminals = client.get("/api/v1/terminals?limit=100", headers=demo).json()
    assert len(branches) == 2
    for b in branches:
        for t in [None] + [t["id"] for t in terminals if t["branch_id"] == b["id"]]:
            token = _login(client, b["id"], t)
            h = {"Authorization": f"Bearer {token}"}
            products = client.get("/api/v1/products?limit=200&offset=0", headers=h).json()
            assert len([p for p in products if p["active"]]) >= 30
            assert client.get("/api/v1/categories?limit=100", headers=h).json()


def test_token_from_reset_database_is_rejected_not_empty(db_session, client):
    run_seed(db_session)
    branch = db_session.query(models.Branch).first()
    stale = _login(client, branch.id)
    # Simulate `docker compose down -v` + reseed: same JWT secret, new ids.
    for m in (models.User, models.Company):
        db_session.query(m).delete()
    db_session.commit()
    r = client.get("/api/v1/products?limit=200&offset=0", headers={"Authorization": f"Bearer {stale}"})
    assert r.status_code == 401


def test_expired_or_garbage_token_is_401(client, db_session):
    r = client.get("/api/v1/products", headers={"Authorization": "Bearer not.a.valid.token"})
    assert r.status_code == 401


def test_upgrade_old_schema_keeps_demo_products(tmp_path):
    """A database created by an older build (no image/attribute/delivery
    columns) must be migrated in place and still list its products."""
    eng = create_engine(f"sqlite:///{tmp_path/'old.db'}")
    Base.metadata.create_all(bind=eng)
    from sqlalchemy.orm import sessionmaker

    S = sessionmaker(bind=eng)
    with S() as s:
        run_seed(s)
    # Strip the columns added in T6 to mimic the pre-upgrade schema.
    new_cols = {"products": ["attributes", "image_source", "image_data"], "companies": ["default_delivery_fee"]}
    with eng.begin() as c:
        for table, cols in new_cols.items():
            for col in cols:
                c.execute(text(f"ALTER TABLE {table} DROP COLUMN {col}"))
    assert "image_data" not in {c["name"] for c in inspect(eng).get_columns("products")}
    added = add_missing_columns(eng)
    assert "products.image_data" in added
    with S() as s:
        run_seed(s)  # skipped: company exists, data kept
        assert s.query(models.Product).filter(models.Product.active == True).count() >= 30  # noqa: E712
