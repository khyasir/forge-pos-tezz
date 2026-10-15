from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import create_access_token, verify_pin

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    branch = db.query(models.Branch).filter(models.Branch.id == payload.branch_id).first()
    if not branch:
        raise HTTPException(404, "Branch not found")

    users = (
        db.query(models.User)
        .filter(models.User.company_id == branch.company_id, models.User.active == True)  # noqa: E712
        .all()
    )
    user = next((u for u in users if verify_pin(payload.pin, u.pin_hash)), None)
    if not user:
        raise HTTPException(401, "Invalid PIN")

    token = create_access_token(user, payload.branch_id, payload.terminal_id)
    return schemas.LoginResponse(access_token=token, user=user)
