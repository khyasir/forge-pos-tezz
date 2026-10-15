from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import AuthContext, get_auth_context, hash_pin

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=list[schemas.UserRead])
def list_users(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    q = db.query(models.User).filter(models.User.company_id == auth.company_id)
    return q.order_by(models.User.id).offset(offset).limit(min(limit, 200)).all()


@router.get("/{user_id}", response_model=schemas.UserRead)
def get_user(user_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    user = (
        db.query(models.User)
        .filter(models.User.id == user_id, models.User.company_id == auth.company_id)
        .first()
    )
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.post("", response_model=schemas.UserRead, status_code=201)
def create_user(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    user = models.User(
        company_id=auth.company_id,
        name=payload.name,
        role=payload.role,
        active=payload.active,
        pin_hash=hash_pin(payload.pin),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=schemas.UserRead)
def update_user(
    user_id: str,
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    user = (
        db.query(models.User)
        .filter(models.User.id == user_id, models.User.company_id == auth.company_id)
        .first()
    )
    if not user:
        raise HTTPException(404, "User not found")
    data = payload.model_dump(exclude_unset=True)
    pin = data.pop("pin", None)
    for k, v in data.items():
        setattr(user, k, v)
    if pin:
        user.pin_hash = hash_pin(pin)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    user = (
        db.query(models.User)
        .filter(models.User.id == user_id, models.User.company_id == auth.company_id)
        .first()
    )
    if not user:
        raise HTTPException(404, "User not found")
    db.delete(user)
    db.commit()
    return None
