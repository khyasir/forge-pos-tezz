from app import models
from app.seed import run_seed


def test_karahi_products_with_half_full_in_name_have_no_size_modifier(db_session):
    run_seed(db_session)
    size_group = db_session.query(models.ModifierGroup).filter(models.ModifierGroup.name == "Karahi size").first()
    karahis = (
        db_session.query(models.Product)
        .filter(models.Product.name.like("%Karahi%"))
        .filter((models.Product.name.like("%Half%")) | (models.Product.name.like("%Full%")))
        .all()
    )
    assert karahis
    for product in karahis:
        group_ids = product.modifier_group_ids.split(",") if product.modifier_group_ids else []
        assert size_group.id not in group_ids, f"{product.name} should not carry the redundant size modifier"


def test_demo_unsynced_orders_seeded_as_local_pending(db_session, client):
    run_seed(db_session)
    rows = db_session.query(models.DemoUnsyncedOrder).all()
    assert len(rows) == 3

    r = client.get("/api/v1/demo/unsynced-orders")
    assert r.status_code == 200
    payloads = r.json()
    assert len(payloads) == 3
    for p in payloads:
        assert p["offline"] is True
        assert p["client_uuid"]


def test_seed_failed_orders_expose_fiscal_error_reason(db_session):
    run_seed(db_session)
    failed = db_session.query(models.Order).filter(models.Order.fiscal_status == "failed").all()
    assert failed
    for order in failed:
        assert order.fiscal_error == "FBR gateway timeout"
