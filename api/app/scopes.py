"""Company data isolation for CRUD resources that have no company_id column.
Each scope filters list/get/patch/delete to the caller's company and checks
the parent record on create."""
from . import models


def _scope(filter_fn, create_fn):
    def scope(q, auth):
        return filter_fn(q, auth)

    scope.check_create = create_fn
    return scope


def _branch_ids(auth):
    from sqlalchemy import select

    return select(models.Branch.id).where(models.Branch.company_id == auth.company_id)


company_scope = _scope(
    lambda q, a: q.filter(models.Company.id == a.company_id),
    lambda db, data, a: False,  # tenants cannot create other companies through the API
)

terminal_scope = _scope(
    lambda q, a: q.filter(models.Terminal.branch_id.in_(_branch_ids(a))),
    lambda db, d, a: db.query(models.Branch).filter_by(id=d.get("branch_id"), company_id=a.company_id).first() is not None,
)

floor_scope = _scope(
    lambda q, a: q.filter(models.Floor.branch_id.in_(_branch_ids(a))),
    lambda db, d, a: db.query(models.Branch).filter_by(id=d.get("branch_id"), company_id=a.company_id).first() is not None,
)


def _floor_ids(a):
    from sqlalchemy import select

    return select(models.Floor.id).where(models.Floor.branch_id.in_(_branch_ids(a)))


table_scope = _scope(
    lambda q, a: q.filter(models.Table.floor_id.in_(_floor_ids(a))),
    lambda db, d, a: db.query(models.Floor).join(models.Branch, models.Floor.branch_id == models.Branch.id)
    .filter(models.Floor.id == d.get("floor_id"), models.Branch.company_id == a.company_id).first() is not None,
)


def _group_ids(a):
    from sqlalchemy import select

    return select(models.ModifierGroup.id).where(models.ModifierGroup.company_id == a.company_id)


modifier_scope = _scope(
    lambda q, a: q.filter(models.Modifier.group_id.in_(_group_ids(a))),
    lambda db, d, a: db.query(models.ModifierGroup).filter_by(id=d.get("group_id"), company_id=a.company_id).first() is not None,
)


def _order_ids(a):
    from sqlalchemy import select

    return select(models.Order.id).where(models.Order.company_id == a.company_id)


payment_scope = _scope(
    lambda q, a: q.filter(models.Payment.order_id.in_(_order_ids(a))),
    lambda db, d, a: db.query(models.Order).filter_by(id=d.get("order_id"), company_id=a.company_id).first() is not None,
)
