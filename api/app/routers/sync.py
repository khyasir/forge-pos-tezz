from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import AuthContext, get_auth_context
from ..services import orders as order_service

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@router.post("/batch", response_model=schemas.SyncBatchResponse)
def sync_batch(
    payload: schemas.SyncBatchRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    results = []
    for order_in in payload.orders:
        order_in.terminal_id = order_in.terminal_id or payload.terminal_id
        order, created = order_service.get_or_create_order(db, auth.company_id, order_in)
        results.append(
            schemas.SyncOrderResult(
                client_uuid=order.client_uuid,
                server_id=order.id,
                status=order.status,
                fiscal_status=order.fiscal_status,
                erp_status=order.erp_status,
            )
        )
    return schemas.SyncBatchResponse(results=results)


@router.get("/status", response_model=schemas.SyncStatusResponse)
def sync_status(
    terminal_id: str | None = None,
    branch_id: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    q = db.query(models.Order).filter(models.Order.company_id == auth.company_id)
    if terminal_id:
        q = q.filter(models.Order.terminal_id == terminal_id)
    if branch_id:
        q = q.filter(models.Order.branch_id == branch_id)
    all_orders = q.order_by(models.Order.created_at.desc()).limit(200).all()

    def overall_status(o: models.Order) -> str:
        if o.fiscal_status == "failed" or o.erp_status == "failed":
            return "failed"
        if o.fiscal_status in ("pending",) or o.erp_status in ("pending",):
            return "pending"
        return "synced"

    synced = sum(1 for o in all_orders if overall_status(o) == "synced")
    pending = sum(1 for o in all_orders if overall_status(o) == "pending")
    failed = sum(1 for o in all_orders if overall_status(o) == "failed")

    orders = [
        schemas.SyncOrderStatus(
            client_uuid=o.client_uuid,
            order_id=o.id,
            order_no=o.order_no,
            status=overall_status(o),
            fiscal_status=o.fiscal_status,
            fiscal_error=o.fiscal_error or "",
            erp_status=o.erp_status,
            erp_error=o.erp_error or "",
            total=o.total,
            created_at=o.created_at,
        )
        for o in all_orders
    ]
    return schemas.SyncStatusResponse(synced=synced, pending=pending, failed=failed, orders=orders)
