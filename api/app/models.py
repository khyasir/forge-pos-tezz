import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Company(Base, TimestampMixin):
    __tablename__ = "companies"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(String(300), default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    ntn: Mapped[str] = mapped_column(String(50), default="")
    strn: Mapped[str] = mapped_column(String(50), default="")
    tax_authority: Mapped[str] = mapped_column(String(20), default="PRA")  # FBR | PRA | SRB

    branches: Mapped[list["Branch"]] = relationship(back_populates="company")


class Branch(Base, TimestampMixin):
    __tablename__ = "branches"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(String(300), default="")
    city: Mapped[str] = mapped_column(String(100), default="")

    company: Mapped["Company"] = relationship(back_populates="branches")
    terminals: Mapped[list["Terminal"]] = relationship(back_populates="branch")


class Terminal(Base, TimestampMixin):
    __tablename__ = "terminals"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    branch_id: Mapped[str] = mapped_column(ForeignKey("branches.id"))
    name: Mapped[str] = mapped_column(String(100))
    device_label: Mapped[str] = mapped_column(String(100), default="")

    branch: Mapped["Branch"] = relationship(back_populates="terminals")


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(150))
    role: Mapped[str] = mapped_column(String(20), default="cashier")  # owner|manager|cashier
    pin_hash: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ApiKey(Base, TimestampMixin):
    __tablename__ = "api_keys"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    key: Mapped[str] = mapped_column(String(80), unique=True)
    label: Mapped[str] = mapped_column(String(100), default="Default key")
    scopes: Mapped[str] = mapped_column(String(50), default="read,write")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Category(Base, TimestampMixin):
    __tablename__ = "categories"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(100))
    name_ur: Mapped[str] = mapped_column(String(100), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Tax(Base, TimestampMixin):
    __tablename__ = "taxes"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(100))
    authority: Mapped[str] = mapped_column(String(20), default="PRA")
    cash_rate: Mapped[float] = mapped_column(Float, default=0.16)
    card_rate: Mapped[float] = mapped_column(Float, default=0.05)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True)


class KitchenStation(Base, TimestampMixin):
    __tablename__ = "kitchen_stations"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(100))


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), nullable=True)
    tax_id: Mapped[str] = mapped_column(ForeignKey("taxes.id"), nullable=True)
    kitchen_station_id: Mapped[str] = mapped_column(
        ForeignKey("kitchen_stations.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(150))
    name_ur: Mapped[str] = mapped_column(String(150), default="")
    sku: Mapped[str] = mapped_column(String(50), default="")
    price: Mapped[float] = mapped_column(Float, default=0)
    pct_code: Mapped[str] = mapped_column(String(20), default="0000.0000")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    modifier_group_ids: Mapped[str] = mapped_column(Text, default="")  # csv of ModifierGroup ids


class ModifierGroup(Base, TimestampMixin):
    __tablename__ = "modifier_groups"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(100))
    name_ur: Mapped[str] = mapped_column(String(100), default="")
    min_select: Mapped[int] = mapped_column(Integer, default=0)
    max_select: Mapped[int] = mapped_column(Integer, default=1)

    modifiers: Mapped[list["Modifier"]] = relationship(back_populates="group")


class Modifier(Base, TimestampMixin):
    __tablename__ = "modifiers"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    group_id: Mapped[str] = mapped_column(ForeignKey("modifier_groups.id"))
    name: Mapped[str] = mapped_column(String(100))
    name_ur: Mapped[str] = mapped_column(String(100), default="")
    price_delta: Mapped[float] = mapped_column(Float, default=0)

    group: Mapped["ModifierGroup"] = relationship(back_populates="modifiers")


class Deal(Base, TimestampMixin):
    __tablename__ = "deals"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(150))
    name_ur: Mapped[str] = mapped_column(String(150), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[float] = mapped_column(Float, default=0)
    tax_id: Mapped[str] = mapped_column(ForeignKey("taxes.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(150), default="")
    phone: Mapped[str] = mapped_column(String(30), default="")
    ntn: Mapped[str] = mapped_column(String(50), default="")
    cnic: Mapped[str] = mapped_column(String(50), default="")


class Floor(Base, TimestampMixin):
    __tablename__ = "floors"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    branch_id: Mapped[str] = mapped_column(ForeignKey("branches.id"))
    name: Mapped[str] = mapped_column(String(100))

    tables: Mapped[list["Table"]] = relationship(back_populates="floor")


class Table(Base, TimestampMixin):
    __tablename__ = "tables"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    floor_id: Mapped[str] = mapped_column(ForeignKey("floors.id"))
    name: Mapped[str] = mapped_column(String(50))
    seats: Mapped[int] = mapped_column(Integer, default=4)
    status: Mapped[str] = mapped_column(String(20), default="free")  # free|occupied

    floor: Mapped["Floor"] = relationship(back_populates="tables")


class PaymentMethod(Base, TimestampMixin):
    __tablename__ = "payment_methods"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(30))  # cash|card|raast_qr|jazzcash|easypaisa
    fiscal_payment_mode: Mapped[int] = mapped_column(Integer, default=1)  # FBR PaymentMode


class Shift(Base, TimestampMixin):
    __tablename__ = "shifts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    branch_id: Mapped[str] = mapped_column(ForeignKey("branches.id"))
    terminal_id: Mapped[str] = mapped_column(ForeignKey("terminals.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    opening_float: Mapped[float] = mapped_column(Float, default=0)
    counted_cash: Mapped[float] = mapped_column(Float, nullable=True)
    expected_cash: Mapped[float] = mapped_column(Float, nullable=True)
    over_short: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|closed
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    client_uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    order_no: Mapped[str] = mapped_column(String(30), default="")
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    branch_id: Mapped[str] = mapped_column(ForeignKey("branches.id"))
    terminal_id: Mapped[str] = mapped_column(ForeignKey("terminals.id"), nullable=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=True)
    shift_id: Mapped[str] = mapped_column(ForeignKey("shifts.id"), nullable=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=True)
    table_id: Mapped[str] = mapped_column(ForeignKey("tables.id"), nullable=True)

    order_type: Mapped[str] = mapped_column(String(20), default="dine_in")
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|paid|void|refunded
    kds_status: Mapped[str] = mapped_column(String(20), default="new")  # new|preparing|done
    source: Mapped[str] = mapped_column(String(20), default="pos")

    subtotal: Mapped[float] = mapped_column(Float, default=0)
    discount: Mapped[float] = mapped_column(Float, default=0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0)
    pos_fee: Mapped[float] = mapped_column(Float, default=0)
    total: Mapped[float] = mapped_column(Float, default=0)

    payment_mode: Mapped[str] = mapped_column(String(20), default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    offline: Mapped[bool] = mapped_column(Boolean, default=False)

    fiscal_status: Mapped[str] = mapped_column(String(20), default="pending")
    fiscal_number: Mapped[str] = mapped_column(String(60), default="")
    fiscal_qr_payload: Mapped[str] = mapped_column(Text, default="")
    fiscal_error: Mapped[str] = mapped_column(Text, default="")

    erp_status: Mapped[str] = mapped_column(String(20), default="pending")
    erp_error: Mapped[str] = mapped_column(Text, default="")

    paid_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    lines: Mapped[list["OrderLine"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderLine(Base, TimestampMixin):
    __tablename__ = "order_lines"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), nullable=True)
    deal_id: Mapped[str] = mapped_column(ForeignKey("deals.id"), nullable=True)
    name_snapshot: Mapped[str] = mapped_column(String(150), default="")
    qty: Mapped[float] = mapped_column(Float, default=1)
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    notes: Mapped[str] = mapped_column(String(300), default="")
    line_total: Mapped[float] = mapped_column(Float, default=0)

    order: Mapped["Order"] = relationship(back_populates="lines")
    modifiers: Mapped[list["OrderLineModifier"]] = relationship(
        back_populates="line", cascade="all, delete-orphan"
    )


class OrderLineModifier(Base):
    __tablename__ = "order_line_modifiers"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    order_line_id: Mapped[str] = mapped_column(ForeignKey("order_lines.id"))
    modifier_id: Mapped[str] = mapped_column(ForeignKey("modifiers.id"), nullable=True)
    name_snapshot: Mapped[str] = mapped_column(String(100), default="")
    price_delta: Mapped[float] = mapped_column(Float, default=0)

    line: Mapped["OrderLine"] = relationship(back_populates="modifiers")


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"))
    payment_method_id: Mapped[str] = mapped_column(ForeignKey("payment_methods.id"))
    amount: Mapped[float] = mapped_column(Float, default=0)
    tendered: Mapped[float] = mapped_column(Float, default=0)
    change: Mapped[float] = mapped_column(Float, default=0)
    reference: Mapped[str] = mapped_column(String(100), default="")

    order: Mapped["Order"] = relationship(back_populates="payments")


class DemoUnsyncedOrder(Base, TimestampMixin):
    """Holds order JSON the seed intentionally keeps off the Order table,
    so the web app can preload them into IndexedDB as 'client pending' carts.
    """

    __tablename__ = "demo_unsynced_orders"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    payload: Mapped[str] = mapped_column(Text)


class Webhook(Base, TimestampMixin):
    __tablename__ = "webhooks"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    url: Mapped[str] = mapped_column(String(500))
    secret: Mapped[str] = mapped_column(String(100))
    events: Mapped[str] = mapped_column(String(300), default="order.paid")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
