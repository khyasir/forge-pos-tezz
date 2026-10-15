import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


@router.get("/unsynced-orders")
def unsynced_orders(db: Session = Depends(get_db)):
    """Orders the seed deliberately keeps off the server, representing
    carts a cashier made while offline. The web app preloads these into
    IndexedDB on first run so the Sync Status demo has something pending.
    """
    rows = db.query(models.DemoUnsyncedOrder).all()
    return [json.loads(r.payload) for r in rows]
