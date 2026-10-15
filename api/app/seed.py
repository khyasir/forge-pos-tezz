"""Demo data seed: one Pakistani restaurant company with realistic menu,
staff, tables, taxes, a couple of orders/shifts, so every page in the web
app has something to show on first run. Runs once -- skipped if a Company
already exists.
"""
import json
import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from . import models, schemas
from .config import get_settings
from .security import hash_pin
from .services import orders as order_service
from .services import pricing

settings = get_settings()

random.seed(42)

# Fixed (not randomly generated) so the web app's build-time
# NEXT_PUBLIC_DEMO_API_KEY can match it for the pre-login branch/terminal
# picker -- this is a sandbox demo key over demo data, never a production
# credential, so a well-known value is fine here.
DEMO_API_KEY = "tz_test_tezzdemo0000000000000001"


def _id() -> str:
    return uuid.uuid4().hex


def run_seed(db: Session) -> None:
    if db.query(models.Company).first():
        return

    company = models.Company(
        id=_id(),
        name="Lahore Karahi House",
        address="12-B Main Boulevard, Gulberg",
        city="Lahore",
        ntn="1234567-8",
        strn="3277876123456",
        tax_authority="PRA",
    )
    db.add(company)
    db.flush()

    gulberg = models.Branch(id=_id(), company_id=company.id, name="Gulberg", address="12-B Main Boulevard", city="Lahore")
    dha = models.Branch(id=_id(), company_id=company.id, name="DHA", address="Y Block Commercial", city="Lahore")
    db.add_all([gulberg, dha])
    db.flush()

    term1 = models.Terminal(id=_id(), branch_id=gulberg.id, name="Terminal 1", device_label="Front counter")
    term2 = models.Terminal(id=_id(), branch_id=dha.id, name="Terminal 1", device_label="Front counter")
    db.add_all([term1, term2])
    db.flush()

    owner = models.User(id=_id(), company_id=company.id, name="Ahmed Khan (Owner)", role="owner", pin_hash=hash_pin("1111"))
    manager = models.User(id=_id(), company_id=company.id, name="Bilal Manager", role="manager", pin_hash=hash_pin("2222"))
    cashier = models.User(id=_id(), company_id=company.id, name="Sana Cashier", role="cashier", pin_hash=hash_pin("3333"))
    db.add_all([owner, manager, cashier])
    db.flush()

    api_key = models.ApiKey(id=_id(), company_id=company.id, key=DEMO_API_KEY, label="Demo sandbox key")
    db.add(api_key)

    tax = models.Tax(id=_id(), company_id=company.id, name="PRA Standard", authority="PRA", cash_rate=0.16, card_rate=0.05, is_default=True)
    db.add(tax)
    db.flush()

    category_defs = ["Karahi", "BBQ", "Rice", "Naan & Roti", "Deals", "Drinks", "Desserts"]
    categories = {}
    for i, name in enumerate(category_defs):
        cat = models.Category(id=_id(), company_id=company.id, name=name, sort_order=i)
        db.add(cat)
        categories[name] = cat
    db.flush()

    stations = {
        name: models.KitchenStation(id=_id(), company_id=company.id, name=name)
        for name in ["Karahi", "BBQ", "Tandoor", "Drinks"]
    }
    db.add_all(stations.values())
    db.flush()

    products_def = [
        ("Chicken Karahi Half", "چکن کڑاہی ہاف", "Karahi", "Karahi", 1450),
        ("Chicken Karahi Full", "چکن کڑاہی فل", "Karahi", "Karahi", 2700),
        ("Mutton Karahi Half", "مٹن کڑاہی ہاف", "Karahi", "Karahi", 1950),
        ("Mutton Karahi Full", "مٹن کڑاہی فل", "Karahi", "Karahi", 3600),
        ("Chicken White Karahi Half", "چکن وائٹ کڑاہی ہاف", "Karahi", "Karahi", 1500),
        ("Chicken White Karahi Full", "چکن وائٹ کڑاہی فل", "Karahi", "Karahi", 2800),
        ("Seekh Kabab (6pc)", "سیخ کباب", "BBQ", "BBQ", 450),
        ("Beef Seekh Kabab (6pc)", "بیف سیخ کباب", "BBQ", "BBQ", 500),
        ("Chicken Tikka (Leg)", "چکن تکہ", "BBQ", "BBQ", 500),
        ("Malai Boti (6pc)", "ملائی بوٹی", "BBQ", "BBQ", 550),
        ("Reshmi Kabab (6pc)", "ریشمی کباب", "BBQ", "BBQ", 550),
        ("Fish Tikka", "فش تکہ", "BBQ", "BBQ", 650),
        ("Chicken Biryani", "چکن بریانی", "Rice", "Karahi", 450),
        ("Kabuli Pulao", "کابلی پلاؤ", "Rice", "Karahi", 500),
        ("Chicken Fried Rice", "چکن فرائیڈ رائس", "Rice", "Karahi", 420),
        ("Vegetable Pulao", "ویجیٹیبل پلاؤ", "Rice", "Karahi", 350),
        ("Plain Naan", "سادہ نان", "Naan & Roti", "Tandoor", 60),
        ("Garlic Naan", "گارلک نان", "Naan & Roti", "Tandoor", 120),
        ("Roghni Naan", "روغنی نان", "Naan & Roti", "Tandoor", 100),
        ("Tandoori Roti", "تندوری روٹی", "Naan & Roti", "Tandoor", 50),
        ("Sheermal", "شیرمال", "Naan & Roti", "Tandoor", 150),
        ("Raita", "رائتہ", "Naan & Roti", "Karahi", 100),
        ("Kachumber Salad", "کچومر سلاد", "Naan & Roti", "Karahi", 150),
        ("Kheer", "کھیر", "Desserts", "Drinks", 200),
        ("Gulab Jamun (2pc)", "گلاب جامن", "Desserts", "Drinks", 180),
        ("Lassi", "لسی", "Drinks", "Drinks", 150),
        ("Mint Margarita", "منٹ مارگریٹا", "Drinks", "Drinks", 200),
        ("Soft Drink 1.5L", "سافٹ ڈرنک 1.5 لیٹر", "Drinks", "Drinks", 250),
        ("Kashmiri Chai", "کشمیری چائے", "Drinks", "Drinks", 180),
        ("Mineral Water", "منرل واٹر", "Drinks", "Drinks", 80),
    ]
    products = {}
    for i, (name, name_ur, cat, station, price) in enumerate(products_def):
        p = models.Product(
            id=_id(),
            company_id=company.id,
            category_id=categories[cat].id,
            tax_id=tax.id,
            kitchen_station_id=stations[station].id,
            name=name,
            name_ur=name_ur,
            sku=f"SKU{i + 1:03d}",
            price=price,
            pct_code="2105.9000" if cat in ("Karahi", "BBQ", "Rice") else "0401.0000",
        )
        db.add(p)
        products[name] = p
    db.flush()

    spice_group = models.ModifierGroup(id=_id(), company_id=company.id, name="Spice level", name_ur="تیزی", min_select=0, max_select=1)
    size_group = models.ModifierGroup(id=_id(), company_id=company.id, name="Karahi size", name_ur="سائز", min_select=0, max_select=1)
    extras_group = models.ModifierGroup(id=_id(), company_id=company.id, name="Extras", name_ur="اضافی", min_select=0, max_select=3)
    naan_group = models.ModifierGroup(id=_id(), company_id=company.id, name="Naan type", name_ur="نان کی قسم", min_select=0, max_select=1)
    db.add_all([spice_group, size_group, extras_group, naan_group])
    db.flush()

    modifiers_def = [
        (spice_group, "Mild", "ہلکا", 0),
        (spice_group, "Medium", "درمیانہ", 0),
        (spice_group, "Hot", "تیز", 0),
        (size_group, "Half", "ہاف", 0),
        (size_group, "Full", "فل", 850),
        (extras_group, "Extra Cheese", "اضافی پنیر", 150),
        (extras_group, "Extra Raita", "اضافی رائتہ", 100),
        (naan_group, "Plain", "سادہ", 0),
        (naan_group, "Garlic", "گارلک", 60),
        (naan_group, "Roghni", "روغنی", 40),
    ]
    for group, name, name_ur, delta in modifiers_def:
        db.add(models.Modifier(id=_id(), group_id=group.id, name=name, name_ur=name_ur, price_delta=delta))
    db.flush()

    karahi_mods = f"{spice_group.id},{size_group.id},{extras_group.id}"
    for name in ["Chicken Karahi Half", "Chicken Karahi Full", "Mutton Karahi Half", "Mutton Karahi Full", "Chicken White Karahi Half", "Chicken White Karahi Full"]:
        products[name].modifier_group_ids = karahi_mods
    for name in ["Plain Naan", "Garlic Naan", "Roghni Naan"]:
        products[name].modifier_group_ids = naan_group.id
    db.commit()

    family_deal = models.Deal(
        id=_id(), company_id=company.id, tax_id=tax.id,
        name="Family Deal", name_ur="فیملی ڈیل",
        description="1 Full Karahi + 4 Naan + 1.5L Soft Drink",
        price=3499,
    )
    student_deal = models.Deal(
        id=_id(), company_id=company.id, tax_id=tax.id,
        name="Student Deal", name_ur="اسٹوڈنٹ ڈیل",
        description="1 Half Karahi + 2 Naan + 1 Soft Drink",
        price=1299,
    )
    db.add_all([family_deal, student_deal])

    ground = models.Floor(id=_id(), branch_id=gulberg.id, name="Ground")
    rooftop = models.Floor(id=_id(), branch_id=gulberg.id, name="Rooftop")
    db.add_all([ground, rooftop])
    db.flush()
    for i in range(1, 9):
        db.add(models.Table(id=_id(), floor_id=ground.id, name=f"T{i}", seats=4))
    for i in range(1, 7):
        db.add(models.Table(id=_id(), floor_id=rooftop.id, name=f"R{i}", seats=6))

    payment_methods_def = [("Cash", "cash", 1), ("Card", "card", 2), ("Raast QR", "raast_qr", 3), ("JazzCash", "jazzcash", 4), ("Easypaisa", "easypaisa", 5)]
    payment_methods = {}
    for name, code, mode in payment_methods_def:
        pm = models.PaymentMethod(id=_id(), company_id=company.id, name=name, code=code, fiscal_payment_mode=mode)
        db.add(pm)
        payment_methods[code] = pm
    db.flush()
    db.commit()

    product_list = list(products.values())

    open_shift = models.Shift(
        id=_id(), branch_id=gulberg.id, terminal_id=term1.id, user_id=cashier.id,
        opening_float=5000, status="open", opened_at=datetime.utcnow() - timedelta(hours=3),
    )
    closed_shift = models.Shift(
        id=_id(), branch_id=gulberg.id, terminal_id=term1.id, user_id=manager.id,
        opening_float=5000, status="closed",
        opened_at=datetime.utcnow() - timedelta(days=1, hours=9),
        closed_at=datetime.utcnow() - timedelta(days=1),
    )
    db.add_all([open_shift, closed_shift])
    db.flush()

    def make_order(branch, terminal, shift, user_id, created_at, pay_code="cash") -> models.Order:
        n_items = random.randint(1, 4)
        lines = []
        for _ in range(n_items):
            prod = random.choice(product_list)
            qty = random.choice([1, 1, 1, 2])
            lines.append(
                schemas.OrderLineIn(
                    product_id=prod.id, name_snapshot=prod.name, qty=qty, unit_price=prod.price,
                )
            )
        payload = schemas.OrderCreate(
            client_uuid=_id(),
            branch_id=branch.id,
            terminal_id=terminal.id,
            user_id=user_id,
            shift_id=shift.id if shift else None,
            order_type=random.choice(["dine_in", "takeaway", "dine_in", "delivery"]),
            created_at=created_at,
            lines=lines,
        )
        order, _ = order_service.get_or_create_order(db, company.id, payload)
        is_cash = pay_code == "cash"
        rate = pricing.tax_rate_for_payment(db, order, is_cash)
        total = round(order.subtotal + order.subtotal * rate + settings.pos_fee_pkr, 2)
        tendered = total if not is_cash else float(((int(total) // 50) + 1) * 50)
        order_service.pay_order(
            db, order,
            [schemas.PaymentIn(payment_method_id=payment_methods[pay_code].id, amount=total, tendered=tendered)],
            None,
        )
        return order

    now = datetime.utcnow()
    all_orders: list[models.Order] = []
    for i in range(25):
        created_at = now - timedelta(hours=random.randint(1, 72))
        pay_code = random.choice(["cash", "cash", "card", "raast_qr", "jazzcash", "easypaisa"])
        if i % 3 == 0:
            order = make_order(dha, term2, None, manager.id, created_at, pay_code)
        elif created_at > open_shift.opened_at:
            order = make_order(gulberg, term1, open_shift, cashier.id, created_at, pay_code)
        else:
            order = make_order(gulberg, term1, closed_shift, manager.id, created_at, pay_code)
        all_orders.append(order)

    # Force 3 orders into a deterministic "fiscal failed" demo state.
    for order in all_orders[:3]:
        order.fiscal_status = "failed"
        order.fiscal_error = "FBR gateway timeout"
        order.fiscal_number = ""
        order.fiscal_qr_payload = ""
    # Force 2 orders into "ERP pending" (not yet pushed).
    for order in all_orders[3:5]:
        order.erp_status = "pending"
        order.erp_error = ""
    db.commit()

    # Close the closed_shift with real counted-cash numbers, same formula
    # the /shifts/{id}/close endpoint uses, so its Z report has real data.
    cash_pm = payment_methods["cash"]
    closed_shift_cash = (
        db.query(models.Payment)
        .join(models.Order, models.Payment.order_id == models.Order.id)
        .filter(models.Order.shift_id == closed_shift.id, models.Payment.payment_method_id == cash_pm.id)
        .all()
    )
    expected = closed_shift.opening_float + sum(p.amount for p in closed_shift_cash)
    closed_shift.expected_cash = round(expected, 2)
    closed_shift.counted_cash = round(expected - 50, 2)  # demo: cashier short by Rs.50
    closed_shift.over_short = round(closed_shift.counted_cash - closed_shift.expected_cash, 2)
    db.commit()

    # 3 "client pending" carts that exist only on the device (never hit the
    # Order table) -- served via /api/v1/demo/unsynced-orders so the web app
    # can preload them into IndexedDB as already-pending local orders.
    for _ in range(3):
        prod = random.choice(product_list)
        payload = {
            "client_uuid": _id(),
            "branch_id": gulberg.id,
            "terminal_id": term1.id,
            "user_id": cashier.id,
            "shift_id": open_shift.id,
            "order_type": "takeaway",
            "offline": True,
            "lines": [
                {
                    "product_id": prod.id,
                    "name_snapshot": prod.name,
                    "qty": 1,
                    "unit_price": prod.price,
                    "modifiers": [],
                }
            ],
        }
        db.add(models.DemoUnsyncedOrder(id=_id(), payload=json.dumps(payload)))
    db.commit()
