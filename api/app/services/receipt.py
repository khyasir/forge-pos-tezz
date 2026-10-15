import io
import os

import qrcode
import qrcode.image.svg
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from .. import models

_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
_env = Environment(loader=FileSystemLoader(_TEMPLATES_DIR), autoescape=True)


def qr_svg(payload: str) -> str:
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(payload, image_factory=factory, box_size=10)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode("utf-8")


def build_receipt_data(db: Session, order: models.Order) -> dict:
    company = db.query(models.Company).filter(models.Company.id == order.company_id).first()
    branch = db.query(models.Branch).filter(models.Branch.id == order.branch_id).first()
    customer = (
        db.query(models.Customer).filter(models.Customer.id == order.customer_id).first()
        if order.customer_id
        else None
    )
    payments = db.query(models.Payment).filter(models.Payment.order_id == order.id).all()

    lines = []
    for line in order.lines:
        mods = [f"{m.name_snapshot} (+{m.price_delta})" if m.price_delta else m.name_snapshot for m in line.modifiers]
        lines.append(
            {
                "name": line.name_snapshot,
                "qty": line.qty,
                "unit_price": line.unit_price,
                "line_total": line.line_total,
                "modifiers": mods,
                "notes": line.notes,
            }
        )

    qr = qr_svg(order.fiscal_qr_payload or order.id) if order.fiscal_status == "ok" else ""

    return {
        "order": order,
        "company": company,
        "branch": branch,
        "customer": customer,
        "lines": lines,
        "payments": payments,
        "qr_svg": qr,
        "is_offline": order.fiscal_status == "offline_mode",
        "is_fiscal_failed": order.fiscal_status == "failed",
        "pos_fee_label": "Rs.1 POS Service Fee",
    }


def render_receipt_html(db: Session, order: models.Order) -> str:
    data = build_receipt_data(db, order)
    template = _env.get_template("receipt.html")
    return template.render(**data)
