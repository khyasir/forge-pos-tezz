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
