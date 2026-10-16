from datetime import datetime, timedelta

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

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
    order.total = round(order.subtotal - order.discount + (order.delivery_fee or 0), 2)


class OrderRejected(ValueError):
    """Payload can never be accepted (e.g. branch of another company)."""


def _resolve_delivery_fee(db: Session, company_id: str, payload: schemas.OrderCreate) -> float:
    if payload.order_type != "delivery":
        return 0.0
    if payload.delivery_fee is not None:
        return max(0.0, round(float(payload.delivery_fee), 2))
    company = db.get(models.Company, company_id)
    return round(company.default_delivery_fee or 0, 2) if company else 0.0


def _clean_refs(db: Session, company_id: str, payload: schemas.OrderCreate) -> None:
    """Optional references from offline devices may be blank or stale (e.g. a
    terminal deleted while the tablet was offline). A bad optional reference
    must never block an order from syncing, so unknown ones become NULL."""
    checks = {
        "terminal_id": lambda v: db.query(models.Terminal).join(models.Branch, models.Terminal.branch_id == models.Branch.id)
        .filter(models.Terminal.id == v, models.Branch.company_id == company_id).first(),
        "user_id": lambda v: db.query(models.User).filter_by(id=v, company_id=company_id).first(),
        "shift_id": lambda v: db.get(models.Shift, v),
        "customer_id": lambda v: db.query(models.Customer).filter_by(id=v, company_id=company_id).first(),
        "table_id": lambda v: db.get(models.Table, v),
    }
    for field, exists in checks.items():
        v = getattr(payload, field)
        if not v or exists(v) is None:
            setattr(payload, field, None)
    for line in payload.lines:
        if line.product_id and db.query(models.Product).filter_by(id=line.product_id, company_id=company_id).first() is None:
            line.product_id = None
        if line.deal_id and db.query(models.Deal).filter_by(id=line.deal_id, company_id=company_id).first() is None:
            line.deal_id = None
        for m in line.modifiers:
            if m.modifier_id and db.get(models.Modifier, m.modifier_id) is None:
                m.modifier_id = None


def get_or_create_order(db: Session, company_id: str, payload: schemas.OrderCreate) -> tuple[models.Order, bool]:
    """Idempotent upsert keyed on client_uuid. Returns (order, created).

    Safe against double-submit and concurrent sync from two tabs/devices: the
    unique index on client_uuid makes the second insert fail and we return the
    first row instead.
    """
    existing = db.query(models.Order).filter(models.Order.client_uuid == payload.client_uuid).first()
    if existing:
        if existing.company_id != company_id:
            raise OrderRejected("client_uuid already used by another company")
        return existing, False

    branch = (
        db.query(models.Branch)
        .filter(models.Branch.id == payload.branch_id, models.Branch.company_id == company_id)
        .first()
    )
    if branch is None:
        raise OrderRejected("Branch not found for this company")
    _clean_refs(db, company_id, payload)
    order = models.Order(
        client_uuid=payload.client_uuid,
        order_no=_next_order_no(db, branch),
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
        delivery_fee=_resolve_delivery_fee(db, company_id, payload),
        delivery_address=(payload.delivery_address or "")[:300],
    )
    if payload.created_at:
        order.created_at = payload.created_at
    try:
        db.add(order)
        db.flush()
        _apply_lines(db, order, payload.lines)
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(models.Order).filter(models.Order.client_uuid == payload.client_uuid).first()
        if existing and existing.company_id == company_id:
            return existing, False
        raise
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


DELIVERY_LINE_NAME = "Delivery Charges"
DELIVERY_PCT_CODE = "9805.9000"  # services; confirm with the client's tax advisor
SENDING_STALE_AFTER = timedelta(minutes=5)
MAX_AUTO_ATTEMPTS = 12


def taxable_value(order: models.Order) -> float:
    """PRA/FBR taxable value: goods/services subtotal plus delivery charges.
    (Discount handling is unchanged from v1: tax is on the pre-discount value.)"""
    return round(order.subtotal + (order.delivery_fee or 0), 2)


def _build_fiscal_invoice(db: Session, order: models.Order, is_cash: bool) -> dict:
    company = db.query(models.Company).filter(models.Company.id == order.company_id).first()
    customer = (
        db.query(models.Customer).filter(models.Customer.id == order.customer_id).first()
        if order.customer_id
        else None
    )
    rate = pricing.tax_rate_for_payment(db, order, is_cash)
    items = []
    for line in order.lines:
        tax_charged = round(line.line_total * rate, 2)
        product = db.get(models.Product, line.product_id) if line.product_id else None
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
    if order.delivery_fee:
        tax_charged = round(order.delivery_fee * rate, 2)
        items.append(
            {
                "ItemCode": "DELIVERY",
                "ItemName": DELIVERY_LINE_NAME,
                "Quantity": 1,
                "PCTCode": DELIVERY_PCT_CODE,
                "TaxRate": rate,
                "SaleValue": order.delivery_fee,
                "TotalAmount": round(order.delivery_fee + tax_charged, 2),
                "TaxCharged": tax_charged,
                "Discount": 0,
                "FurtherTax": 0,
                "InvoiceType": 1,
                "RefUSIN": "",
            }
        )
    return {
        "USIN": order.id,
        "DateTime": (order.paid_at or datetime.utcnow()).isoformat(),
        "BuyerNTN": customer.ntn if customer else "",
        "BuyerCNIC": customer.cnic if customer else "",
        "BuyerName": customer.name if customer else "",
        "BuyerPhoneNumber": customer.phone if customer else "",
        "TotalBillAmount": order.total,
        "TotalQuantity": sum(l.qty for l in order.lines) + (1 if order.delivery_fee else 0),
        "TotalSaleValue": taxable_value(order),
        "TotalTaxCharged": order.tax_amount,
        "Discount": order.discount,
        "FurtherTax": 0,
        "PaymentMode": 1 if is_cash else 2,
        "RefUSIN": "",
        "InvoiceType": 1,
        "Items": items,
        "_company_strn": company.strn if company else "",
    }


def _claim(db: Session, order: models.Order, field: str, from_states: tuple[str, ...], to_state: str) -> bool:
    """Atomic compare-and-set on a status column. Only one request/worker/tab
    can win, which is what prevents duplicate payments, duplicate FBR invoices
    and duplicate Odoo orders on double-click, retry and reconnect."""
    col = getattr(models.Order, field)
    res = db.execute(
        update(models.Order)
        .where(models.Order.id == order.id, col.in_(from_states))
        .values({field: to_state, "updated_at": datetime.utcnow()})
    )
    db.commit()
    db.refresh(order)
    return res.rowcount == 1


def pay_order(db: Session, order: models.Order, payments_in: list[schemas.PaymentIn], customer_phone: str | None) -> models.Order:
    if order.status != "open":
        raise ValueError(f"Order is {order.status}, cannot pay")
    methods = {}
    for p in payments_in:
        pm = (
            db.query(models.PaymentMethod)
            .filter(models.PaymentMethod.id == p.payment_method_id, models.PaymentMethod.company_id == order.company_id)
            .first()
        )
        if pm is None:
            raise ValueError("Unknown payment method")
        methods[p.payment_method_id] = pm
    if not _claim(db, order, "status", ("open",), "paying"):
        raise ValueError(f"Order is {order.status}, cannot pay")

    is_cash = all(methods[p.payment_method_id].code == "cash" for p in payments_in)
    rate = pricing.tax_rate_for_payment(db, order, is_cash)
    order.tax_amount = round(taxable_value(order) * rate, 2)
    order.pos_fee = settings.pos_fee_pkr
    order.total = round(order.subtotal - order.discount + (order.delivery_fee or 0) + order.tax_amount + order.pos_fee, 2)

    for p_in in payments_in:
        change = max(0.0, (p_in.tendered or p_in.amount) - p_in.amount)
        db.add(
            models.Payment(
                order_id=order.id,
                payment_method_id=p_in.payment_method_id,
                amount=p_in.amount,
                tendered=p_in.tendered or p_in.amount,
                change=change,
                reference=p_in.reference,
            )
        )

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


def _schedule_retry(order: models.Order) -> None:
    attempts = max(order.fiscal_attempts or 0, order.erp_attempts or 0)
    delay = min(30 * (2 ** max(attempts - 1, 0)), 3600)  # 30s, 60s, 2m, 4m ... max 1h
    order.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)


def run_fiscal(db: Session, order: models.Order, is_cash: bool | None = None) -> models.Order:
    # Orders rung up offline are fiscalized as soon as they reach the server
    # (FBR expects offline invoices within 24h). `order.offline` is kept for reporting.
    if order.fiscal_status == "ok":
        return order
    if not _claim(db, order, "fiscal_status", ("pending", "failed", "offline_mode"), "sending"):
        return order  # someone else is sending it right now, or it is already ok

    if is_cash is None:
        is_cash = order.payment_mode == "cash"
    invoice = _build_fiscal_invoice(db, order, is_cash)
    adapter = get_fiscal_adapter()
    try:
        result = adapter.fiscalize(invoice)
    except Exception as exc:  # noqa: BLE001
        from ..adapters.fiscal.base import FiscalResult

        result = FiscalResult(ok=False, error=f"{type(exc).__name__}")
    order.fiscal_attempts = (order.fiscal_attempts or 0) + 1
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
        _schedule_retry(order)
        send_event(db, order.company_id, "fiscal.failed", {"id": order.id, "error": result.error})
    db.commit()
    db.refresh(order)
    return order


def build_erp_payload(db: Session, order: models.Order) -> dict:
    def ref(line):
        if not getattr(line, "product_id", None):
            return ""
        prod = db.get(models.Product, line.product_id)
        return prod.erp_ref if prod else ""

    return {
        "id": order.id,
        "usin": order.client_uuid,
        "order_no": order.order_no,
        "order_type": order.order_type,
        "total": order.total,
        "delivery_fee": order.delivery_fee or 0,
        "delivery_address": order.delivery_address or "",
        "lines": [
            {
                "name": l.name_snapshot
                + (" + " + ", ".join(m.name_snapshot for m in l.modifiers) if l.modifiers else ""),
                "qty": l.qty,
                "price": round(l.unit_price + sum(m.price_delta for m in l.modifiers), 2),
                "erp_product_ref": ref(l),
            }
            for l in order.lines
        ],
    }


def run_erp_push(db: Session, order: models.Order) -> models.Order:
    if order.erp_status == "ok":
        return order
    if not _claim(db, order, "erp_status", ("pending", "failed"), "sending"):
        return order
    adapter = get_erp_adapter()
    payload = build_erp_payload(db, order)
    if not any(l["erp_product_ref"] for l in payload["lines"]):
        # Company not linked to an ERP (e.g. demo data): keep the local mock flow.
        from ..adapters.erp.mock import MockERPAdapter
        adapter = MockERPAdapter()
    try:
        result = adapter.push_order(payload)
    except Exception as exc:  # noqa: BLE001
        from ..adapters.erp.base import ERPPushResult

        result = ERPPushResult(ok=False, error=type(exc).__name__)
    order.erp_attempts = (order.erp_attempts or 0) + 1
    if result.ok:
        order.erp_status = "ok"
        order.erp_error = ""
        order.erp_ref = result.erp_ref
    else:
        order.erp_status = "failed"
        order.erp_error = result.error
        _schedule_retry(order)
        send_event(db, order.company_id, "sync.failed", {"id": order.id, "target": "erp", "error": result.error})
    db.commit()
    db.refresh(order)
    return order


def recover_stale_sending(db: Session) -> int:
    """A crash mid-push leaves status 'sending'. After 5 minutes we assume the
    worker died and allow a retry (the FBR/Odoo calls are idempotent on USIN)."""
    cutoff = datetime.utcnow() - SENDING_STALE_AFTER
    n = 0
    for field in ("fiscal_status", "erp_status"):
        col = getattr(models.Order, field)
        res = db.execute(
            update(models.Order)
            .where(col == "sending", models.Order.updated_at < cutoff)
            .values({field: "failed", "updated_at": datetime.utcnow()})
        )
        n += res.rowcount
    res = db.execute(
        update(models.Order)
        .where(models.Order.status == "paying", models.Order.updated_at < cutoff)
        .values(status="open", updated_at=datetime.utcnow())
    )
    n += res.rowcount
    db.commit()
    return n


def retry_due_orders(db: Session, now: datetime | None = None, limit: int = 50) -> dict:
    """Automatic retry with exponential backoff for paid orders whose FBR or
    Odoo push failed. Called by the background worker every 15s."""
    now = now or datetime.utcnow()
    recover_stale_sending(db)
    q = (
        db.query(models.Order)
        .filter(models.Order.status.in_(("paid", "refunded")))
        .filter((models.Order.fiscal_status.in_(("failed", "offline_mode", "pending"))) | (models.Order.erp_status.in_(("failed", "pending"))))
        .filter((models.Order.next_retry_at == None) | (models.Order.next_retry_at <= now))  # noqa: E711
        .filter(models.Order.fiscal_attempts < MAX_AUTO_ATTEMPTS)
        .order_by(models.Order.created_at)
        .limit(limit)
    )
    stats = {"fiscal": 0, "erp": 0}
    for order in q.all():
        if order.fiscal_status in ("failed", "offline_mode", "pending"):
            run_fiscal(db, order)
            stats["fiscal"] += 1
        if order.erp_status in ("failed", "pending") and (order.erp_attempts or 0) < MAX_AUTO_ATTEMPTS:
            run_erp_push(db, order)
            stats["erp"] += 1
    return stats


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
