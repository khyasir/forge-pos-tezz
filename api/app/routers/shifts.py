from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import AuthContext, get_auth_context

router = APIRouter(prefix="/api/v1/shifts", tags=["shifts"])


def _company_shift(db: Session, auth: AuthContext, shift_id: str) -> models.Shift:
    shift = (
        db.query(models.Shift)
        .join(models.Branch, models.Shift.branch_id == models.Branch.id)
        .filter(models.Shift.id == shift_id, models.Branch.company_id == auth.company_id)
        .first()
    )
    if not shift:
        raise HTTPException(404, "Shift not found")
    return shift


@router.get("", response_model=list[schemas.ShiftRead])
def list_shifts(
    branch_id: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    q = db.query(models.Shift).join(models.Branch, models.Shift.branch_id == models.Branch.id).filter(
        models.Branch.company_id == auth.company_id
    )
    if branch_id:
        q = q.filter(models.Shift.branch_id == branch_id)
    if status:
        q = q.filter(models.Shift.status == status)
    return q.order_by(models.Shift.opened_at.desc()).all()


@router.get("/{shift_id}", response_model=schemas.ShiftRead)
def get_shift(shift_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    return _company_shift(db, auth, shift_id)


@router.post("", response_model=schemas.ShiftRead, status_code=201)
def open_shift(
    payload: schemas.ShiftCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    existing = (
        db.query(models.Shift)
        .filter(models.Shift.terminal_id == payload.terminal_id, models.Shift.status == "open")
        .first()
    )
    if existing:
        raise HTTPException(400, "Terminal already has an open shift")
    shift = models.Shift(**payload.model_dump())
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return shift


@router.post("/{shift_id}/close", response_model=schemas.ShiftRead)
def close_shift(
    shift_id: str,
    payload: schemas.ShiftCloseRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    shift = _company_shift(db, auth, shift_id)
    if shift.status == "closed":
        raise HTTPException(400, "Shift already closed")

    cash_sales = (
        db.query(models.Payment)
        .join(models.Order, models.Payment.order_id == models.Order.id)
        .join(models.PaymentMethod, models.Payment.payment_method_id == models.PaymentMethod.id)
        .filter(models.Order.shift_id == shift_id, models.PaymentMethod.code == "cash")
        .all()
    )
    expected = shift.opening_float + sum(p.amount for p in cash_sales)

    shift.counted_cash = payload.counted_cash
    shift.expected_cash = expected
    shift.over_short = round(payload.counted_cash - expected, 2)
    shift.status = "closed"
    shift.closed_at = datetime.utcnow()
    db.commit()
    db.refresh(shift)
    return shift


@router.get("/{shift_id}/z-report")
def z_report(shift_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    shift = _company_shift(db, auth, shift_id)
    orders = (
        db.query(models.Order)
        .filter(models.Order.shift_id == shift_id, models.Order.status.in_(["paid", "refunded"]))
        .all()
    )
    payments = (
        db.query(models.Payment)
        .join(models.Order, models.Payment.order_id == models.Order.id)
        .filter(models.Order.shift_id == shift_id)
        .all()
    )
    by_method: dict[str, float] = {}
    for p in payments:
        method = db.query(models.PaymentMethod).filter(models.PaymentMethod.id == p.payment_method_id).first()
        key = method.name if method else p.payment_method_id
        by_method[key] = round(by_method.get(key, 0) + p.amount, 2)

    return {
        "shift_id": shift.id,
        "status": shift.status,
        "opened_at": shift.opened_at,
        "closed_at": shift.closed_at,
        "opening_float": shift.opening_float,
        "counted_cash": shift.counted_cash,
        "expected_cash": shift.expected_cash,
        "over_short": shift.over_short,
        "order_count": len(orders),
        "gross_sales": round(sum(o.subtotal for o in orders), 2),
        "discounts": round(sum(o.discount for o in orders), 2),
        "tax_collected": round(sum(o.tax_amount for o in orders), 2),
        "pos_fees": round(sum(o.pos_fee for o in orders), 2),
        "net_total": round(sum(o.total for o in orders), 2),
        "by_payment_method": by_method,
        "fiscal_ok": sum(1 for o in orders if o.fiscal_status == "ok"),
        "fiscal_failed": sum(1 for o in orders if o.fiscal_status == "failed"),
    }
