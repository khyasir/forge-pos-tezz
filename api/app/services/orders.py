from datetime import datetime

from sqlalchemy.orm import Session

from .. import models, schemas
from ..adapters.erp import get_erp_adapter
from ..adapters.fiscal import get_fiscal_adapter
from ..config import get_settings
from . import pricing
from .webhooks import send_event

settings = get_settings()


def _next_order_no(db: Session, branch: models.Branch) -> str:
    count = db.query(models.Order).filter(models.Order.branch_id == branch.id).count()
    prefix = "".join(w[0] for w in branch.name.split()[:3]).upper() or "ORD"
    return f"{prefix}-{count + 1:05d}"


def _apply_lines(db: Session, order: models.Order, lines: list[schemas.OrderLineIn]) -> None:
    order.lines.clear()
    for line_in in lines:
        deltas = [m.price_delta for m in line_in.modifiers]
        line = models.OrderLine(
            order_id=order.id,
            product_id=line_in.product_id,
            deal_id=line_in.deal_id,
            name_snapshot=line_in.name_snapshot,
            qty=line_in.qty,
            unit_price=line_in.unit_price,
            notes=line_in.notes,
            line_total=pricing.compute_line_total(line_in.qty, line_in.unit_price, deltas),
        )
        for mod_in in line_in.modifiers:
            line.modifiers.append(
                models.OrderLineModifier(
                    modifier_id=mod_in.modifier_id,
                    name_snapshot=mod_in.name_snapshot,
                    price_delta=mod_in.price_delta,
                )
            )
        order.lines.append(line)
    order.subtotal = pricing.compute_subtotal(order)
    order.total = round(order.subtotal - order.discount, 2)


def get_or_create_order(db: Session, company_id: str, payload: schemas.OrderCreate) -> tuple[models.Order, bool]:
    """Idempotent upsert keyed on client_uuid. Returns (order, created)."""
    existing = db.query(models.Order).filter(models.Order.client_uuid == payload.client_uuid).first()
    if existing:
        return existing, False

    branch = db.query(models.Branch).filter(models.Branch.id == payload.branch_id).first()
    order = models.Order(
        client_uuid=payload.client_uuid,
        order_no=_next_order_no(db, branch) if branch else payload.client_uuid[:8],
        company_id=company_id,
        branch_id=payload.branch_id,
        terminal_id=payload.terminal_id,
        user_id=payload.user_id,
        shift_id=payload.shift_id,
        customer_id=payload.customer_id,
        table_id=payload.table_id,
        order_type=payload.order_type,
        source=payload.source,
        discount=payload.discount,
        notes=payload.notes,
        offline=payload.offline,
    )
    if payload.created_at:
        order.created_at = payload.created_at
    db.add(order)
    db.flush()
    _apply_lines(db, order, payload.lines)
    db.commit()
    db.refresh(order)
    send_event(db, company_id, "order.created", {"id": order.id, "order_no": order.order_no})
    return order, True


def update_order_lines(db: Session, order: models.Order, lines: list[schemas.OrderLineIn], discount: float | None) -> models.Order:
    if discount is not None:
        order.discount = discount
    _apply_lines(db, order, lines)
    db.commit()
    db.refresh(order)
    return order


def _build_fiscal_invoice(db: Session, order: models.Order, is_cash: bool) -> dict:
    company = db.query(models.Company).filter(models.Company.id == order.company_id).first()
    customer = (
        db.query(models.Customer).filter(models.Customer.id == order.customer_id).first()
        if order.customer_id
        else None
    )
    items = []
    for line in order.lines:
        rate = pricing.tax_rate_for_payment(db, order, is_cash)
        tax_charged = round(line.line_total * rate, 2)
        product = (
            db.query(models.Product).filter(models.Product.id == line.product_id).first()
            if line.product_id
            else None
        )
        items.append(
            {
                "ItemCode": product.sku if product else "",
                "ItemName": line.name_snapshot,
                "Quantity": line.qty,
                "PCTCode": product.pct_code if product else "0000.0000",
                "TaxRate": rate,
                "SaleValue": line.line_total,
                "TotalAmount": round(line.line_total + tax_charged, 2),
                "TaxCharged": tax_charged,
                "Discount": 0,
                "FurtherTax": 0,
                "InvoiceType": 1,
                "RefUSIN": "",
            }
        )
    return {
        "USIN": order.id,
        "DateTime": datetime.utcnow().isoformat(),
        "BuyerNTN": customer.ntn if customer else "",
        "BuyerCNIC": customer.cnic if customer else "",
        "BuyerName": customer.name if customer else "",
        "BuyerPhoneNumber": customer.phone if customer else "",
        "TotalBillAmount": order.total,
        "TotalQuantity": sum(l.qty for l in order.lines),
        "TotalSaleValue": order.subtotal,
        "TotalTaxCharged": order.tax_amount,
        "Discount": order.discount,
        "FurtherTax": 0,
        "PaymentMode": 1 if is_cash else 2,
        "RefUSIN": "",
        "InvoiceType": 1,
        "Items": items,
        "_company_strn": company.strn if company else "",
    }


def pay_order(db: Session, order: models.Order, payments_in: list[schemas.PaymentIn], customer_phone: str | None) -> models.Order:
    if order.status != "open":
        raise ValueError(f"Order is {order.status}, cannot pay")

    is_cash = all(
        db.query(models.PaymentMethod).filter(models.PaymentMethod.id == p.payment_method_id).first().code
        == "cash"
        for p in payments_in
    )
    rate = pricing.tax_rate_for_payment(db, order, is_cash)
    order.tax_amount = round(order.subtotal * rate, 2)
    order.pos_fee = settings.pos_fee_pkr
    order.total = round(order.subtotal - order.discount + order.tax_amount + order.pos_fee, 2)

    total_tendered = 0.0
    total_amount = 0.0
    for p_in in payments_in:
        change = max(0.0, (p_in.tendered or p_in.amount) - p_in.amount)
        payment = models.Payment(
            order_id=order.id,
            payment_method_id=p_in.payment_method_id,
            amount=p_in.amount,
            tendered=p_in.tendered or p_in.amount,
            change=change,
            reference=p_in.reference,
        )
        db.add(payment)
        total_tendered += payment.tendered
        total_amount += p_in.amount

    order.payment_mode = "cash" if is_cash else "card"
    order.status = "paid"
    order.paid_at = datetime.utcnow()
    db.commit()
    db.refresh(order)

    if order.table_id:
        table = db.query(models.Table).filter(models.Table.id == order.table_id).first()
        if table:
            table.status = "free"
            db.commit()

    run_fiscal(db, order, is_cash=is_cash)
    run_erp_push(db, order)

    send_event(
        db,
        order.company_id,
        "order.paid",
        {"id": order.id, "order_no": order.order_no, "total": order.total},
    )
    return order


def run_fiscal(db: Session, order: models.Order, is_cash: bool | None = None) -> models.Order:
    if order.offline:
        order.fiscal_status = "offline_mode"
        db.commit()
        db.refresh(order)
        return order

    if is_cash is None:
        is_cash = order.payment_mode == "cash"
    invoice = _build_fiscal_invoice(db, order, is_cash)
    adapter = get_fiscal_adapter()
    result = adapter.fiscalize(invoice)
    if result.ok:
        order.fiscal_status = "ok"
        order.fiscal_number = result.fiscal_number
        order.fiscal_qr_payload = result.qr_payload
        order.fiscal_error = ""
        send_event(
            db, order.company_id, "fiscal.succeeded", {"id": order.id, "fiscal_number": result.fiscal_number}
        )
    else:
        order.fiscal_status = "failed"
        order.fiscal_error = result.error
        send_event(db, order.company_id, "fiscal.failed", {"id": order.id, "error": result.error})
    db.commit()
    db.refresh(order)
    return order


def run_erp_push(db: Session, order: models.Order) -> models.Order:
    adapter = get_erp_adapter()
    payload = {
        "id": order.id,
        "usin": order.client_uuid,
        "order_no": order.order_no,
        "total": order.total,
        "lines": [
            {
                "name": l.name_snapshot,
                "qty": l.qty,
                "price": l.unit_price,
                "erp_product_ref": (db.get(models.Product, l.product_id).erp_ref if getattr(l, "product_id", None) and db.get(models.Product, l.product_id) else ""),
            }
            for l in order.lines
        ],
    }
    if not any(l["erp_product_ref"] for l in payload["lines"]):
        # Company not linked to an ERP (e.g. demo data): keep the local mock flow.
        from ..adapters.erp.mock import MockERPAdapter
        adapter = MockERPAdapter()
    result = adapter.push_order(payload)
    if result.ok:
        order.erp_status = "ok"
        order.erp_error = ""
        order.erp_ref = result.erp_ref
    else:
        order.erp_status = "failed"
        order.erp_error = result.error
        send_event(db, order.company_id, "sync.failed", {"id": order.id, "target": "erp", "error": result.error})
    db.commit()
    db.refresh(order)
    return order


def void_order(db: Session, order: models.Order) -> models.Order:
    if order.status == "paid":
        raise ValueError("Paid orders must be refunded, not voided")
    order.status = "void"
    db.commit()
    db.refresh(order)
    send_event(db, order.company_id, "order.voided", {"id": order.id, "order_no": order.order_no})
    return order


def refund_order(db: Session, order: models.Order, reason: str) -> models.Order:
    if order.status != "paid":
        raise ValueError("Only paid orders can be refunded")
    order.status = "refunded"
    order.notes = (order.notes + f"\nRefund: {reason}").strip()
    db.commit()
    db.refresh(order)
    send_event(db, order.company_id, "order.refunded", {"id": order.id, "order_no": order.order_no, "reason": reason})
    return order
