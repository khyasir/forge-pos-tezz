# Tezz POS API contract (for the web app build)

Base URL at runtime: `NEXT_PUBLIC_API_URL` (default `http://localhost:8000` in dev; in
docker-compose the web container reaches the api container directly and Next.js
rewrites `/api/*` on the public port to it).

Auth: every endpoint except `GET /health`, `POST /api/v1/auth/login`, and
`GET /api/v1/demo/unsynced-orders` requires header `Authorization: Bearer <token>`.
`<token>` is either a JWT (returned by login) or a sandbox API key (starts `tz_test_`).
For the **pre-login branch/terminal picker on /login**, use a hardcoded demo API key
from `NEXT_PUBLIC_DEMO_API_KEY`. This value is NOT random: the seed always creates it
as the fixed string `tz_test_tezzdemo0000000000000001` (see `api/app/seed.py`
`DEMO_API_KEY`) specifically so a build-time `NEXT_PUBLIC_` env var can match it -- use
that exact value as the default in `.env.example`. After PIN login, store and use the
returned JWT for everything else (JWT also carries role: owner|manager|cashier).

All list endpoints: `GET <resource>?limit=50&offset=0&updated_since=<ISO8601>` →
JSON array (no envelope). Single: `GET <resource>/{id}`. Create: `POST <resource>`
(the created resource is returned incl. server-assigned `id`, `created_at`,
`updated_at`; omit `id`/`company_id` in the request body, server fills it from
auth). Update: `PATCH <resource>/{id}` (partial body). Delete: `DELETE <resource>/{id}`
→ 204.

## Generic CRUD resources (list/get/post/patch/delete as above)
- `/api/v1/branches` {id, company_id, name, address, city, created_at, updated_at}
- `/api/v1/terminals` {id, branch_id, name, device_label, ...}
- `/api/v1/users` {id, company_id, name, role(owner|manager|cashier), active, ...} — POST/PATCH also take `pin` (string) which the server hashes; GET never returns a pin.
- `/api/v1/api-keys` {id, company_id, key, label, scopes, active, ...} — `key` is plaintext (sandbox demo), shown on the admin API Keys tab.
- `/api/v1/categories` {id, company_id, name, name_ur, sort_order, ...}
- `/api/v1/taxes` {id, company_id, name, authority, cash_rate, card_rate, is_default, ...} (rates are fractions, e.g. 0.16)
- `/api/v1/kitchen-stations` {id, company_id, name}
- `/api/v1/products` {id, company_id, category_id, tax_id, kitchen_station_id, name, name_ur, sku, price, pct_code, active, modifier_group_ids} — `modifier_group_ids` is a **comma-separated string** of ModifierGroup ids applicable to this product (empty string if none); split on `,` client-side.
- `/api/v1/modifier-groups` {id, company_id, name, name_ur, min_select, max_select, modifiers: [ {id, group_id, name, name_ur, price_delta} ]} — nested `modifiers` on read.
- `/api/v1/modifiers` {id, group_id, name, name_ur, price_delta} (flat CRUD too, used by /admin)
- `/api/v1/deals` {id, company_id, name, name_ur, description, price, tax_id, active}
- `/api/v1/customers` {id, company_id, name, phone, ntn, cnic}
- `/api/v1/floors` {id, branch_id, name, tables: [ {id, floor_id, name, seats, status(free|occupied)} ]} — nested `tables` on read.
- `/api/v1/tables` {id, floor_id, name, seats, status} (flat CRUD too)
- `/api/v1/payment-methods` {id, company_id, name, code(cash|card|raast_qr|jazzcash|easypaisa), fiscal_payment_mode}
- `/api/v1/payments` {id, order_id, payment_method_id, amount, tendered, change, reference} — mostly read-only from the UI side (created via the pay action below).
- `/api/v1/webhooks` {id, company_id, url, secret, events (csv string), active}

## Auth
`POST /api/v1/auth/login` body `{branch_id, terminal_id?, pin}` →
`{access_token, token_type:"bearer", user:{id,name,role,company_id,active,created_at,updated_at}}`.
PIN logins seeded: owner `1111`, manager `2222`, cashier `3333` (any branch of the seeded company).

## Orders
Order shape (`OrderRead`):
```
{ id, client_uuid, order_no, company_id, branch_id, terminal_id, user_id, shift_id,
  customer_id, table_id, order_type(dine_in|takeaway|delivery), status(open|paid|void|refunded),
  kds_status(new|preparing|done), source, subtotal, discount, tax_amount, pos_fee, total,
  payment_mode, notes, offline(bool), fiscal_status(pending|ok|failed|offline_mode),
  fiscal_number, fiscal_qr_payload, fiscal_error, erp_status(pending|ok|failed), erp_error,
  paid_at, created_at, updated_at,
  lines: [ { id, product_id, deal_id, name_snapshot, qty, unit_price, notes, line_total,
             modifiers: [ {id, modifier_id, name_snapshot, price_delta} ] } ] }
```
- `GET /api/v1/orders?status=&branch_id=&updated_since=&limit=&offset=`
- `GET /api/v1/orders/{id}`
- `POST /api/v1/orders` body (`OrderCreate`):
  ```
  { client_uuid (required, client-generated uuid, used as the idempotency key),
    branch_id (required), terminal_id?, user_id?, shift_id?, customer_id?, table_id?,
    order_type?, source? ("pos" default, use "whatsapp" etc for other channels),
    discount?, notes?, offline? (bool, true if the device was offline when the order was made),
    created_at? (ISO8601, only meaningful for offline/backfilled orders),
    lines: [ { product_id?, deal_id?, name_snapshot (required, snapshot the product name text),
               qty, unit_price (required, snapshot the current price), notes?,
               modifiers: [ {modifier_id?, name_snapshot, price_delta} ] } ] }
  ```
  Creating with a `client_uuid` that already exists on the server returns the existing
  order unchanged (idempotent) rather than erroring — this is also how offline sync works.
- `PATCH /api/v1/orders/{id}` body `{table_id?, notes?, discount?, lines?}` — only allowed while `status=open`; sending `lines` replaces the whole line list and recomputes `subtotal`/`total`.
- `POST /api/v1/orders/{id}/send-to-kitchen` — marks the order's table occupied; returns the order.
- `POST /api/v1/orders/{id}/kds-status` body `{kds_status: "new"|"preparing"|"done"}` → order (this is what the KDS Start/Done buttons call).
- `POST /api/v1/orders/{id}/pay` body:
  ```
  { payments: [ {payment_method_id, amount, tendered?, reference?} ],  // amount should equal order.total for a single tender; split into multiple entries for split bills, amounts summing to order.total
    customer_phone?: string }  // optional, attaches/creates a Customer by phone
  ```
  Server computes `tax_amount` (cash vs card/digital rate from the Tax config) and adds the
  Rs.1 POS fee itself — **do not** add fee/tax client-side, just show `order.total` after pay
  succeeds. Returns the paid order with `fiscal_status`/`fiscal_number`/`erp_status` filled in
  synchronously (the mock adapters respond immediately). If the order was created with
  `offline: true`, `fiscal_status` becomes `"offline_mode"` instead of being fiscalized —
  show "OFFLINE MODE - fiscal number pending" on the local receipt in that case, and let the
  user retry fiscalization later from the Sync page (`POST /api/v1/fiscal/{order_id}/retry`
  after flipping offline off is NOT automatic — for the demo, once an offline order has synced
  to the server via `/sync/batch`, call `POST /api/v1/fiscal/{order_id}/retry` to fiscalize it).
- `POST /api/v1/orders/{id}/void` — only for `status=open` orders.
- `POST /api/v1/orders/{id}/refund` body `{reason?}` — only for `status=paid` orders.
- `GET /api/v1/orders/{id}/receipt` → same `OrderRead` JSON (use for the offline/local receipt view).
- `GET /api/v1/orders/{id}/receipt.html` → fully rendered HTML receipt (SRO 1006 fields, QR
  svg, fiscal number) — fetch this (with the Authorization header) and render it in an
  iframe/new window for printing when the order is synced + fiscalized.

## Offline sync (the core offline-first requirement)
- `POST /api/v1/sync/batch` body `{terminal_id, orders: [ <OrderCreate>, ... ]}` (send oldest-first,
  up to ~50 at a time) → `{results: [ {client_uuid, server_id, status, fiscal_status, erp_status} ] }`.
  Safe to resend the same batch (upsert by `client_uuid`).
- `GET /api/v1/sync/status?terminal_id=&branch_id=` →
  `{synced, pending, failed, orders: [ {client_uuid, order_id, order_no, status(synced|pending|failed), fiscal_status, erp_status, total, created_at} ]}`.
- `GET /api/v1/fiscal/status` → `{ok, pending, failed, offline_mode}` counts.
- `POST /api/v1/fiscal/{order_id}/retry` → re-run fiscalization on a paid order, returns the order.
- `GET /api/v1/erp/status` → `{ok, pending, failed}` counts.
- `POST /api/v1/erp/{order_id}/retry` → re-push to ERP, returns the order.
- `GET /api/v1/demo/unsynced-orders` (no auth) → array of `OrderCreate`-shaped JSON objects
  that exist ONLY on this endpoint (never created server-side). On first app load (no existing
  IndexedDB data), fetch this and insert each as a LOCAL/pending order in IndexedDB so the
  Sync Status page has something "pending" to demo immediately, without the user ringing up
  anything yet.

## Shifts
- `GET /api/v1/shifts?branch_id=&status=` / `GET /api/v1/shifts/{id}`
- `POST /api/v1/shifts` body `{branch_id, terminal_id, user_id, opening_float}` → 400 if that
  terminal already has an open shift.
- `POST /api/v1/shifts/{id}/close` body `{counted_cash}` → closed shift with
  `expected_cash`/`counted_cash`/`over_short` filled in.
- `GET /api/v1/shifts/{id}/z-report` →
  `{shift_id, status, opened_at, closed_at, opening_float, counted_cash, expected_cash,
    over_short, order_count, gross_sales, discounts, tax_collected, pos_fees, net_total,
    by_payment_method: {<method name>: amount}, fiscal_ok, fiscal_failed}`.

## Errors
Standard FastAPI `{"detail": "..."}` on 4xx. 401 on missing/bad credentials, 404 on
not-found-or-not-yours (company-scoped), 400 on invalid state transitions (e.g. paying
an already-paid order, opening a second shift on a terminal).

## Seeded demo data (for building against)
Company "Lahore Karahi House" (PRA, Lahore), branches "Gulberg" and "DHA", 7 categories,
~29 products (Urdu names in `name_ur`), modifier groups (Spice level, Karahi size, Extras,
Naan type), 2 deals, 1 default Tax (16% cash / 5% card), floors "Ground" (T1-T8) and
"Rooftop" (R1-R6) on the Gulberg branch, 5 payment methods, PIN logins 1111/2222/3333,
~25 historic orders (3 forced `fiscal_status=failed` with error "FBR gateway timeout",
2 forced `erp_status=pending`), one open shift, one closed shift with real Z-report numbers,
and 3 demo "client pending" carts only reachable via `/api/v1/demo/unsynced-orders`.
