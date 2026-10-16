// TypeScript mirrors of api/app/schemas.py. Keep in sync with the backend
// contract (ground truth lives in that file, not here).

export interface CompanyRead {
  id: string;
  name: string;
  address: string;
  city: string;
  ntn: string;
  strn: string;
  tax_authority: string;
  default_delivery_fee: number;
  created_at: string;
  updated_at: string;
}

export interface BranchRead {
  id: string;
  company_id: string;
  name: string;
  address: string;
  city: string;
  created_at: string;
  updated_at: string;
}

export interface TerminalRead {
  id: string;
  branch_id: string;
  name: string;
  device_label: string;
  created_at: string;
  updated_at: string;
}

export interface UserRead {
  id: string;
  company_id: string;
  name: string;
  role: "owner" | "manager" | "cashier" | string;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ApiKeyRead {
  id: string;
  company_id: string;
  label: string;
  scopes: string;
  active: boolean;
  key: string;
  created_at: string;
  updated_at: string;
}

export interface CategoryRead {
  id: string;
  company_id: string;
  name: string;
  name_ur: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface TaxRead {
  id: string;
  company_id: string;
  name: string;
  authority: string;
  cash_rate: number;
  card_rate: number;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface KitchenStationRead {
  id: string;
  company_id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface ProductRead {
  id: string;
  company_id: string;
  category_id?: string | null;
  tax_id?: string | null;
  kitchen_station_id?: string | null;
  name: string;
  name_ur: string;
  sku: string;
  price: number;
  pct_code: string;
  active: boolean;
  modifier_group_ids: string;
  attributes?: string;
  image_url?: string;
  created_at: string;
  updated_at: string;
}

export interface ModifierRead {
  id: string;
  group_id: string;
  name: string;
  name_ur: string;
  price_delta: number;
  created_at: string;
  updated_at: string;
}

export interface ModifierGroupRead {
  id: string;
  company_id: string;
  name: string;
  name_ur: string;
  min_select: number;
  max_select: number;
  modifiers: ModifierRead[];
  created_at: string;
  updated_at: string;
}

export interface DealRead {
  id: string;
  company_id: string;
  name: string;
  name_ur: string;
  description: string;
  price: number;
  tax_id?: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CustomerRead {
  id: string;
  company_id: string;
  name: string;
  phone: string;
  ntn: string;
  cnic: string;
  created_at: string;
  updated_at: string;
}

export interface TableRead {
  id: string;
  floor_id: string;
  name: string;
  seats: number;
  status: "free" | "occupied" | string;
  created_at: string;
  updated_at: string;
}

export interface FloorRead {
  id: string;
  branch_id: string;
  name: string;
  tables: TableRead[];
  created_at: string;
  updated_at: string;
}

export interface PaymentMethodRead {
  id: string;
  company_id: string;
  name: string;
  code: string;
  fiscal_payment_mode: number;
  created_at: string;
  updated_at: string;
}

export interface ShiftRead {
  id: string;
  branch_id: string;
  terminal_id: string;
  user_id: string;
  opening_float: number;
  counted_cash?: number | null;
  expected_cash?: number | null;
  over_short?: number | null;
  status: "open" | "closed" | string;
  opened_at: string;
  closed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrderLineModifierIn {
  modifier_id?: string | null;
  name_snapshot: string;
  price_delta: number;
}

export interface OrderLineModifierRead extends OrderLineModifierIn {
  id: string;
}

export interface OrderLineIn {
  product_id?: string | null;
  deal_id?: string | null;
  name_snapshot: string;
  qty: number;
  unit_price: number;
  notes: string;
  modifiers: OrderLineModifierIn[];
}

export interface OrderLineRead extends OrderLineIn {
  id: string;
  line_total: number;
  modifiers: OrderLineModifierRead[];
}

export type OrderType = "dine_in" | "takeaway" | "delivery";

export interface OrderCreate {
  client_uuid: string;
  branch_id: string;
  terminal_id?: string | null;
  user_id?: string | null;
  shift_id?: string | null;
  customer_id?: string | null;
  table_id?: string | null;
  order_type: OrderType;
  source: string;
  discount: number;
  notes: string;
  offline: boolean;
  created_at?: string | null;
  delivery_fee?: number | null;
  delivery_address?: string;
  lines: OrderLineIn[];
}

export interface OrderRead {
  id: string;
  client_uuid: string;
  order_no: string;
  company_id: string;
  branch_id: string;
  terminal_id?: string | null;
  user_id?: string | null;
  shift_id?: string | null;
  customer_id?: string | null;
  table_id?: string | null;
  order_type: string;
  status: "open" | "paid" | "void" | "refunded" | string;
  kds_status: "new" | "preparing" | "done" | string;
  source: string;
  subtotal: number;
  discount: number;
  tax_amount: number;
  pos_fee: number;
  delivery_fee?: number;
  delivery_address?: string;
  total: number;
  payment_mode: string;
  notes: string;
  offline: boolean;
  fiscal_status: "pending" | "ok" | "failed" | "offline_mode" | string;
  fiscal_number: string;
  fiscal_qr_payload: string;
  fiscal_error: string;
  erp_status: "pending" | "ok" | "failed" | string;
  erp_error: string;
  paid_at?: string | null;
  created_at: string;
  updated_at: string;
  lines: OrderLineRead[];
}

export interface PaymentIn {
  payment_method_id: string;
  amount: number;
  tendered: number;
  reference: string;
}

export interface PayRequest {
  payments: PaymentIn[];
  customer_phone?: string | null;
}

export interface KdsStatusRequest {
  kds_status: "new" | "preparing" | "done";
}

export interface LoginRequest {
  branch_id: string;
  terminal_id?: string | null;
  pin: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserRead;
}

export interface SyncOrderResult {
  client_uuid: string;
  server_id: string;
  status: string;
  fiscal_status: string;
  erp_status: string;
  error?: string;
}

export interface SyncBatchResponse {
  results: SyncOrderResult[];
}

export interface SyncOrderStatus {
  client_uuid: string;
  order_id: string;
  order_no: string;
  status: "synced" | "pending" | "failed" | string;
  fiscal_status: string;
  fiscal_error: string;
  erp_status: string;
  erp_error: string;
  total: number;
  created_at: string;
}

export interface SyncStatusResponse {
  synced: number;
  pending: number;
  failed: number;
  orders: SyncOrderStatus[];
}

export interface ZReport {
  shift_id: string;
  status: string;
  opened_at: string;
  closed_at?: string | null;
  opening_float: number;
  counted_cash?: number | null;
  expected_cash?: number | null;
  over_short?: number | null;
  order_count: number;
  gross_sales: number;
  discounts: number;
  tax_collected: number;
  pos_fees: number;
  net_total: number;
  by_payment_method: Record<string, number>;
  fiscal_ok: number;
  fiscal_failed: number;
}
