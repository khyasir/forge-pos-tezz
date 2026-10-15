from .. import models


def compute_line_total(qty: float, unit_price: float, modifier_price_deltas: list[float]) -> float:
    return round((unit_price + sum(modifier_price_deltas)) * qty, 2)


def compute_subtotal(order: models.Order) -> float:
    return round(sum(line.line_total for line in order.lines), 2)


def tax_rate_for_payment(db, order: models.Order, is_cash: bool) -> float:
    """Looks up the first line's product tax config, falling back to the
    company default tax. Cash and card/digital rates differ per PRA rules.
    """
    tax = None
    for line in order.lines:
        if line.product_id:
            product = db.query(models.Product).filter(models.Product.id == line.product_id).first()
            if product and product.tax_id:
                tax = db.query(models.Tax).filter(models.Tax.id == product.tax_id).first()
                break
    if tax is None:
        tax = (
            db.query(models.Tax)
            .filter(models.Tax.company_id == order.company_id, models.Tax.is_default == True)  # noqa: E712
            .first()
        )
    if tax is None:
        return 0.0
    return tax.cash_rate if is_cash else tax.card_rate
