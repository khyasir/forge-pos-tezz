from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import AuthContext, get_auth_context
from ..services import orders as order_service

router = APIRouter(prefix="/api/v1/erp", tags=["erp"])


@router.get("/status")
def erp_status(db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    q = db.query(models.Order).filter(models.Order.company_id == auth.company_id)
    return {
        "ok": q.filter(models.Order.erp_status == "ok").count(),
        "pending": q.filter(models.Order.erp_status == "pending").count(),
        "failed": q.filter(models.Order.erp_status == "failed").count(),
    }


@router.post("/{order_id}/retry", response_model=schemas.OrderRead)
def retry_erp(order_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    order = (
        db.query(models.Order)
        .filter(models.Order.id == order_id, models.Order.company_id == auth.company_id)
        .first()
    )
    if not order:
        raise HTTPException(404, "Order not found")
    if order.status != "paid":
        raise HTTPException(400, "Only paid orders can be re-pushed to ERP")
    return order_service.run_erp_push(db, order)


@router.post("/import", summary="Import categories, products, taxes, modifiers and customers from the configured Odoo")
def erp_import(db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    from ..adapters.erp.odoo_wags import OdooWagsAdapter
    from ..config import get_settings
    from ..services.erp_import import run_import

    if get_settings().erp_provider != "odoo_wags":
        raise HTTPException(400, "ERP_PROVIDER is not odoo_wags")
    if auth.user is not None and auth.user.role not in ("owner", "manager"):
        raise HTTPException(403, "Owner or manager only")
    try:
        return run_import(db, OdooWagsAdapter())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Odoo import failed: {type(exc).__name__}")
