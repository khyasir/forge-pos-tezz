from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import AuthContext, get_auth_context
from ..services import orders as order_service
from ..services.receipt import render_receipt_html

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


def _get_order(db: Session, auth: AuthContext, order_id: str) -> models.Order:
    order = (
        db.query(models.Order)
        .filter(models.Order.id == order_id, models.Order.company_id == auth.company_id)
        .first()
    )
    if not order:
        raise HTTPException(404, "Order not found")
    return order


@router.get("", response_model=list[schemas.OrderRead])
def list_orders(
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    branch_id: str | None = None,
    updated_since: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    q = db.query(models.Order).filter(models.Order.company_id == auth.company_id)
    if status:
        q = q.filter(models.Order.status == status)
    if branch_id:
        q = q.filter(models.Order.branch_id == branch_id)
    if updated_since:
        q = q.filter(models.Order.updated_at >= updated_since)
    return q.order_by(models.Order.created_at.desc()).offset(offset).limit(min(limit, 200)).all()


@router.get("/{order_id}", response_model=schemas.OrderRead)
def get_order(order_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    return _get_order(db, auth, order_id)


@router.post("", response_model=schemas.OrderRead, status_code=201)
def create_order(
    payload: schemas.OrderCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    order, _created = order_service.get_or_create_order(db, auth.company_id, payload)
    return order


@router.patch("/{order_id}", response_model=schemas.OrderRead)
def update_order(
    order_id: str,
    payload: schemas.OrderUpdate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    order = _get_order(db, auth, order_id)
    if order.status != "open":
        raise HTTPException(400, "Only open orders can be edited")
    if payload.table_id is not None:
        order.table_id = payload.table_id
    if payload.notes is not None:
        order.notes = payload.notes
    if payload.lines is not None:
        order_service.update_order_lines(db, order, payload.lines, payload.discount)
    else:
        db.commit()
        db.refresh(order)
    return order


@router.post("/{order_id}/send-to-kitchen", response_model=schemas.OrderRead)
def send_to_kitchen(order_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    order = _get_order(db, auth, order_id)
    if order.table_id:
        table = db.query(models.Table).filter(models.Table.id == order.table_id).first()
        if table:
            table.status = "occupied"
    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/kds-status", response_model=schemas.OrderRead)
def set_kds_status(
    order_id: str,
    payload: schemas.KdsStatusRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    order = _get_order(db, auth, order_id)
    if payload.kds_status not in ("new", "preparing", "done"):
        raise HTTPException(400, "Invalid kds_status")
    order.kds_status = payload.kds_status
    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/pay", response_model=schemas.OrderRead)
def pay_order(
    order_id: str,
    payload: schemas.PayRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    order = _get_order(db, auth, order_id)
    if payload.customer_phone and not order.customer_id:
        customer = (
            db.query(models.Customer)
            .filter(models.Customer.company_id == auth.company_id, models.Customer.phone == payload.customer_phone)
            .first()
        )
        if not customer:
            customer = models.Customer(company_id=auth.company_id, phone=payload.customer_phone)
            db.add(customer)
            db.commit()
            db.refresh(customer)
        order.customer_id = customer.id
        db.commit()
    try:
        return order_service.pay_order(db, order, payload.payments, payload.customer_phone)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.post("/{order_id}/void", response_model=schemas.OrderRead)
def void_order(order_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    order = _get_order(db, auth, order_id)
    try:
        return order_service.void_order(db, order)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.post("/{order_id}/refund", response_model=schemas.OrderRead)
def refund_order(
    order_id: str,
    payload: schemas.RefundRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    order = _get_order(db, auth, order_id)
    try:
        return order_service.refund_order(db, order, payload.reason)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/{order_id}/receipt", response_model=schemas.OrderRead)
def get_receipt_json(order_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    return _get_order(db, auth, order_id)


@router.get("/{order_id}/receipt.html", response_class=Response)
def get_receipt_html(order_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    order = _get_order(db, auth, order_id)
    html = render_receipt_html(db, order)
    return Response(content=html, media_type="text/html")
