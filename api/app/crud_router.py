"""Generic CRUD router factory.

Keeps the plain-CRUD resources (branches, terminals, categories, ...) to a
single declarative call instead of hand-writing list/get/post/patch/delete
for each one.
"""
from typing import Any, Type

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db
from .security import AuthContext, get_auth_context


def make_crud_router(
    *,
    model: Type[Any],
    create_schema: Type[BaseModel],
    update_schema: Type[BaseModel],
    read_schema: Type[BaseModel],
    prefix: str,
    tags: list[str],
    company_scoped: bool = True,
    parent_field: str | None = None,
) -> APIRouter:
    """Build list/get/post/patch/delete endpoints for a SQLAlchemy model.

    company_scoped: filter by the caller's company_id (model must have that
    column, or parent_field pointing at a related company-scoped table is
    used when the model itself has no company_id, e.g. Modifier -> group).
    """
    router = APIRouter(prefix=prefix, tags=tags)
    has_company_col = hasattr(model, "company_id")
    has_updated_at = hasattr(model, "updated_at")

    def _scope_query(q, auth: AuthContext):
        if company_scoped and has_company_col:
            q = q.filter(model.company_id == auth.company_id)
        return q

    @router.get("", response_model=list[read_schema])
    def list_items(
        limit: int = 50,
        offset: int = 0,
        updated_since: str | None = None,
        db: Session = Depends(get_db),
        auth: AuthContext = Depends(get_auth_context),
    ):
        q = db.query(model)
        q = _scope_query(q, auth)
        if updated_since and has_updated_at:
            q = q.filter(model.updated_at >= updated_since)
        return q.order_by(model.id).offset(offset).limit(min(limit, 200)).all()

    @router.get("/{item_id}", response_model=read_schema)
    def get_item(
        item_id: str,
        db: Session = Depends(get_db),
        auth: AuthContext = Depends(get_auth_context),
    ):
        q = _scope_query(db.query(model).filter(model.id == item_id), auth)
        item = q.first()
        if not item:
            raise HTTPException(404, f"{model.__name__} not found")
        return item

    @router.post("", response_model=read_schema, status_code=201)
    def create_item(
        payload: create_schema,
        db: Session = Depends(get_db),
        auth: AuthContext = Depends(get_auth_context),
    ):
        data = payload.model_dump()
        if has_company_col and company_scoped:
            data["company_id"] = auth.company_id
        item = model(**data)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @router.patch("/{item_id}", response_model=read_schema)
    def update_item(
        item_id: str,
        payload: update_schema,
        db: Session = Depends(get_db),
        auth: AuthContext = Depends(get_auth_context),
    ):
        q = _scope_query(db.query(model).filter(model.id == item_id), auth)
        item = q.first()
        if not item:
            raise HTTPException(404, f"{model.__name__} not found")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(item, k, v)
        db.commit()
        db.refresh(item)
        return item

    @router.delete("/{item_id}", status_code=204)
    def delete_item(
        item_id: str,
        db: Session = Depends(get_db),
        auth: AuthContext = Depends(get_auth_context),
    ):
        q = _scope_query(db.query(model).filter(model.id == item_id), auth)
        item = q.first()
        if not item:
            raise HTTPException(404, f"{model.__name__} not found")
        db.delete(item)
        db.commit()
        return None

    return router
