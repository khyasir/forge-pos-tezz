from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Company ----------
class CompanyBase(ORMBase):
    name: str
    address: str = ""
    city: str = ""
    ntn: str = ""
    strn: str = ""
    tax_authority: str = "PRA"


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(ORMBase):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    ntn: Optional[str] = None
    strn: Optional[str] = None
    tax_authority: Optional[str] = None


class CompanyRead(CompanyBase):
    id: str
    created_at: datetime
    updated_at: datetime


# ---------- Branch ----------
class BranchBase(ORMBase):
    company_id: str
    name: str
    address: str = ""
    city: str = ""


class BranchCreate(BranchBase):
    pass


class BranchUpdate(ORMBase):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None


class BranchRead(BranchBase):
    id: str
    created_at: datetime
    updated_at: datetime


# ---------- Terminal ----------
class TerminalBase(ORMBase):
    branch_id: str
    name: str
    device_label: str = ""


class TerminalCreate(TerminalBase):
    pass


class TerminalUpdate(ORMBase):
    name: Optional[str] = None
    device_label: Optional[str] = None


class TerminalRead(TerminalBase):
    id: str
    created_at: datetime
    updated_at: datetime


# ---------- User ----------
class UserBase(ORMBase):
    company_id: str
    name: str
    role: str = "cashier"
    active: bool = True


class UserCreate(UserBase):
    pin: str


class UserUpdate(ORMBase):
    name: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None
    pin: Optional[str] = None


class UserRead(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime


# ---------- ApiKey ----------
class ApiKeyBase(ORMBase):
    company_id: str
    label: str = "Default key"
    scopes: str = "read,write"
    active: bool = True


class ApiKeyCreate(ApiKeyBase):
    sandbox: bool = True


class ApiKeyUpdate(ORMBase):
    label: Optional[str] = None
    active: Optional[bool] = None


class ApiKeyRead(ApiKeyBase):
    id: str
    key: str
    created_at: datetime
    updated_at: datetime


# ---------- Category ----------
class CategoryBase(ORMBase):
    company_id: str
    name: str
    name_ur: str = ""
    sort_order: int = 0


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(ORMBase):
    name: Optional[str] = None
    name_ur: Optional[str] = None
    sort_order: Optional[int] = None


class CategoryRead(CategoryBase):
    id: str
    created_at: datetime
    updated_at: datetime


# ---------- Tax ----------
class TaxBase(ORMBase):
    company_id: str
    name: str
    authority: str = "PRA"
    cash_rate: float = 0.16
    card_rate: float = 0.05
    is_default: bool = True


class TaxCreate(TaxBase):
    pass


class TaxUpdate(ORMBase):
    name: Optional[str] = None
    authority: Optional[str] = None
    cash_rate: Optional[float] = None
    card_rate: Optional[float] = None
    is_default: Optional[bool] = None


class TaxRead(TaxBase):
    id: str
    created_at: datetime
    updated_at: datetime


# ---------- KitchenStation ----------
class KitchenStationBase(ORMBase):
    company_id: str
    name: str


class KitchenStationCreate(KitchenStationBase):
    pass


class KitchenStationUpdate(ORMBase):
    name: Optional[str] = None


class KitchenStationRead(KitchenStationBase):
    id: str
    created_at: datetime
    updated_at: datetime


# ---------- Product ----------
class ProductBase(ORMBase):
    company_id: str
    category_id: Optional[str] = None
    tax_id: Optional[str] = None
    kitchen_station_id: Optional[str] = None
    name: str
    name_ur: str = ""
    sku: str = ""
    price: float = 0
    pct_code: str = "0000.0000"
    active: bool = True
    modifier_group_ids: str = ""


class ProductCreate(ProductBase):
    pass


class ProductUpdate(ORMBase):
    category_id: Optional[str] = None
    tax_id: Optional[str] = None
    kitchen_station_id: Optional[str] = None
    name: Optional[str] = None
    name_ur: Optional[str] = None
    sku: Optional[str] = None
    price: Optional[float] = None
    pct_code: Optional[str] = None
    active: Optional[bool] = None
    modifier_group_ids: Optional[str] = None


class ProductRead(ProductBase):
    id: str
    created_at: datetime
    updated_at: datetime


# ---------- ModifierGroup / Modifier ----------
class ModifierBase(ORMBase):
    group_id: str
    name: str
    name_ur: str = ""
    price_delta: float = 0


class ModifierCreate(ModifierBase):
    pass


class ModifierUpdate(ORMBase):
    name: Optional[str] = None
    name_ur: Optional[str] = None
    price_delta: Optional[float] = None


class ModifierRead(ModifierBase):
    id: str
    created_at: datetime
    updated_at: datetime


class ModifierGroupBase(ORMBase):
    company_id: str
    name: str
    name_ur: str = ""
    min_select: int = 0
    max_select: int = 1


class ModifierGroupCreate(ModifierGroupBase):
    pass


class ModifierGroupUpdate(ORMBase):
    name: Optional[str] = None
    name_ur: Optional[str] = None
    min_select: Optional[int] = None
    max_select: Optional[int] = None


class ModifierGroupRead(ModifierGroupBase):
    id: str
    created_at: datetime
    updated_at: datetime
    modifiers: list[ModifierRead] = []


# ---------- Deal ----------
class DealBase(ORMBase):
    company_id: str
    name: str
    name_ur: str = ""
    description: str = ""
    price: float = 0
    tax_id: Optional[str] = None
    active: bool = True


class DealCreate(DealBase):
    pass


class DealUpdate(ORMBase):
    name: Optional[str] = None
    name_ur: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    tax_id: Optional[str] = None
    active: Optional[bool] = None


class DealRead(DealBase):
    id: str
    created_at: datetime
    updated_at: datetime


# ---------- Customer ----------
class CustomerBase(ORMBase):
    company_id: str
    name: str = ""
    phone: str = ""
    ntn: str = ""
    cnic: str = ""


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(ORMBase):
    name: Optional[str] = None
    phone: Optional[str] = None
    ntn: Optional[str] = None
    cnic: Optional[str] = None


class CustomerRead(CustomerBase):
    id: str
    created_at: datetime
    updated_at: datetime


# ---------- Floor / Table ----------
class TableBase(ORMBase):
    floor_id: str
    name: str
    seats: int = 4
    status: str = "free"


class TableCreate(TableBase):
    pass


class TableUpdate(ORMBase):
    name: Optional[str] = None
    seats: Optional[int] = None
    status: Optional[str] = None


class TableRead(TableBase):
    id: str
    created_at: datetime
    updated_at: datetime


class FloorBase(ORMBase):
    branch_id: str
    name: str


class FloorCreate(FloorBase):
    pass


class FloorUpdate(ORMBase):
    name: Optional[str] = None


class FloorRead(FloorBase):
    id: str
    created_at: datetime
    updated_at: datetime
    tables: list[TableRead] = []


# ---------- PaymentMethod ----------
class PaymentMethodBase(ORMBase):
    company_id: str
    name: str
    code: str
    fiscal_payment_mode: int = 1


class PaymentMethodCreate(PaymentMethodBase):
    pass


class PaymentMethodUpdate(ORMBase):
    name: Optional[str] = None
    code: Optional[str] = None
    fiscal_payment_mode: Optional[int] = None


class PaymentMethodRead(PaymentMethodBase):
    id: str
    created_at: datetime
    updated_at: datetime


# ---------- Shift ----------
class ShiftBase(ORMBase):
    branch_id: str
    terminal_id: str
    user_id: str
    opening_float: float = 0


class ShiftCreate(ShiftBase):
    pass


class ShiftCloseRequest(BaseModel):
    counted_cash: float


class ShiftRead(ORMBase):
    id: str
    branch_id: str
    terminal_id: str
    user_id: str
    opening_float: float
    counted_cash: Optional[float] = None
    expected_cash: Optional[float] = None
    over_short: Optional[float] = None
    status: str
    opened_at: datetime
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ---------- OrderLineModifier / OrderLine ----------
class OrderLineModifierIn(BaseModel):
    modifier_id: Optional[str] = None
    name_snapshot: str = ""
    price_delta: float = 0


class OrderLineModifierRead(ORMBase):
    id: str
    modifier_id: Optional[str] = None
    name_snapshot: str
    price_delta: float


class OrderLineIn(BaseModel):
    product_id: Optional[str] = None
    deal_id: Optional[str] = None
    name_snapshot: str = ""
    qty: float = 1
    unit_price: float = 0
    notes: str = ""
    modifiers: list[OrderLineModifierIn] = []


class OrderLineRead(ORMBase):
    id: str
    product_id: Optional[str] = None
    deal_id: Optional[str] = None
    name_snapshot: str
    qty: float
    unit_price: float
    notes: str
    line_total: float
    modifiers: list[OrderLineModifierRead] = []


# ---------- Order ----------
class OrderCreate(BaseModel):
    client_uuid: str
    branch_id: str
    terminal_id: Optional[str] = None
    user_id: Optional[str] = None
    shift_id: Optional[str] = None
    customer_id: Optional[str] = None
    table_id: Optional[str] = None
    order_type: str = "dine_in"
    source: str = "pos"
    discount: float = 0
    notes: str = ""
    offline: bool = False
    created_at: Optional[datetime] = None
    lines: list[OrderLineIn] = []


class OrderUpdate(BaseModel):
    table_id: Optional[str] = None
    notes: Optional[str] = None
    discount: Optional[float] = None
    lines: Optional[list[OrderLineIn]] = None


class OrderRead(ORMBase):
    id: str
    client_uuid: str
    order_no: str
    company_id: str
    branch_id: str
    terminal_id: Optional[str] = None
    user_id: Optional[str] = None
    shift_id: Optional[str] = None
    customer_id: Optional[str] = None
    table_id: Optional[str] = None
    order_type: str
    status: str
    kds_status: str
    source: str
    subtotal: float
    discount: float
    tax_amount: float
    pos_fee: float
    total: float
    payment_mode: str
    notes: str
    offline: bool
    fiscal_status: str
    fiscal_number: str
    fiscal_qr_payload: str
    fiscal_error: str
    erp_status: str
    erp_error: str
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    lines: list[OrderLineRead] = []


# ---------- Payment ----------
class PaymentIn(BaseModel):
    payment_method_id: str
    amount: float
    tendered: float = 0
    reference: str = ""


class PaymentCreate(BaseModel):
    order_id: str
    payment_method_id: str
    amount: float
    tendered: float = 0
    change: float = 0
    reference: str = ""


class PaymentUpdate(BaseModel):
    amount: Optional[float] = None
    tendered: Optional[float] = None
    reference: Optional[str] = None


class PaymentRead(ORMBase):
    id: str
    order_id: str
    payment_method_id: str
    amount: float
    tendered: float
    change: float
    reference: str
    created_at: datetime


class PayRequest(BaseModel):
    payments: list[PaymentIn]
    customer_phone: Optional[str] = None


class RefundRequest(BaseModel):
    reason: str = ""


class KdsStatusRequest(BaseModel):
    kds_status: str  # new|preparing|done


# ---------- Webhook ----------
class WebhookBase(ORMBase):
    company_id: str
    url: str
    secret: str
    events: str = "order.paid"
    active: bool = True


class WebhookCreate(WebhookBase):
    pass


class WebhookUpdate(ORMBase):
    url: Optional[str] = None
    secret: Optional[str] = None
    events: Optional[str] = None
    active: Optional[bool] = None


class WebhookRead(WebhookBase):
    id: str
    created_at: datetime
    updated_at: datetime


# ---------- Auth ----------
class LoginRequest(BaseModel):
    branch_id: str
    terminal_id: Optional[str] = None
    pin: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


# ---------- Sync ----------
class SyncBatchRequest(BaseModel):
    terminal_id: str
    orders: list[OrderCreate]


class SyncOrderResult(BaseModel):
    client_uuid: str
    server_id: str
    status: str
    fiscal_status: str
    erp_status: str


class SyncBatchResponse(BaseModel):
    results: list[SyncOrderResult]


class SyncOrderStatus(BaseModel):
    client_uuid: str
    order_id: str
    order_no: str
    status: str
    fiscal_status: str
    erp_status: str
    total: float
    created_at: datetime


class SyncStatusResponse(BaseModel):
    synced: int
    pending: int
    failed: int
    orders: list[SyncOrderStatus]
