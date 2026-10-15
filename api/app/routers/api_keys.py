from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import AuthContext, generate_api_key, get_auth_context

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


@router.get("", response_model=list[schemas.ApiKeyRead])
def list_keys(db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    return db.query(models.ApiKey).filter(models.ApiKey.company_id == auth.company_id).all()


@router.post("", response_model=schemas.ApiKeyRead, status_code=201)
def create_key(
    payload: schemas.ApiKeyCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    key = models.ApiKey(
        company_id=auth.company_id,
        key=generate_api_key(payload.sandbox),
        label=payload.label,
        scopes=payload.scopes,
        active=payload.active,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return key


@router.patch("/{key_id}", response_model=schemas.ApiKeyRead)
def update_key(
    key_id: str,
    payload: schemas.ApiKeyUpdate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    key = (
        db.query(models.ApiKey)
        .filter(models.ApiKey.id == key_id, models.ApiKey.company_id == auth.company_id)
        .first()
    )
    if not key:
        raise HTTPException(404, "API key not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(key, k, v)
    db.commit()
    db.refresh(key)
    return key


@router.delete("/{key_id}", status_code=204)
def delete_key(key_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    key = (
        db.query(models.ApiKey)
        .filter(models.ApiKey.id == key_id, models.ApiKey.company_id == auth.company_id)
        .first()
    )
    if not key:
        raise HTTPException(404, "API key not found")
    db.delete(key)
    db.commit()
    return None
