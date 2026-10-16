import base64
import binascii
import re

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import AuthContext, get_auth_context

router = APIRouter(prefix="/api/v1/products", tags=["products"])

MAX_BYTES = 1_500_000
_DATA_URL = re.compile(r"^data:(image/(?:png|jpeg|webp|gif|svg\+xml));base64,(.+)$", re.S)


class ImageUpload(BaseModel):
    data_url: str  # "data:image/png;base64,...."


@router.get("/{product_id}/image", summary="Product image (public, cacheable)")
def get_image(product_id: str, db: Session = Depends(get_db)):
    p = db.get(models.Product, product_id)
    m = _DATA_URL.match(p.image_data) if p and p.image_data else None
    if not m:
        raise HTTPException(404, "No image")
    return Response(
        content=base64.b64decode(m.group(2)),
        media_type=m.group(1),
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.put("/{product_id}/image", response_model=schemas.ProductRead, summary="Upload/replace product image (data URL, max 1.5 MB)")
def put_image(product_id: str, body: ImageUpload, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    p = db.query(models.Product).filter(models.Product.id == product_id, models.Product.company_id == auth.company_id).first()
    if not p:
        raise HTTPException(404, "Product not found")
    if auth.user is not None and auth.user.role not in ("owner", "manager"):
        raise HTTPException(403, "Owner or manager only")
    m = _DATA_URL.match(body.data_url.strip())
    if not m:
        raise HTTPException(400, "Send a base64 data URL of a PNG, JPEG, WEBP, GIF or SVG image")
    try:
        raw = base64.b64decode(m.group(2), validate=True)
    except binascii.Error:
        raise HTTPException(400, "Invalid base64")
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "Image too large (max 1.5 MB)")
    p.image_data = body.data_url.strip()
    p.image_source = "upload"
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{product_id}/image", response_model=schemas.ProductRead, summary="Remove product image")
def delete_image(product_id: str, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    p = db.query(models.Product).filter(models.Product.id == product_id, models.Product.company_id == auth.company_id).first()
    if not p:
        raise HTTPException(404, "Product not found")
    p.image_data = ""
    p.image_source = ""
    db.commit()
    db.refresh(p)
    return p
