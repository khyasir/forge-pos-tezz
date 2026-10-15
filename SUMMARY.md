# Tezz POS — build summary

Demo-ready v1 of a FBR/PRA-ready restaurant POS for Pakistan, per `TASK.md` and
`docs-POS_PLAN.md` (sections 12-14). Monorepo: `api/` (FastAPI/SQLAlchemy 2) + `web/`
(Next.js 14 PWA), wired together by `docker-compose.yml`.

## What was built

### Backend (`api/`)
- Full data model: Company > Branch > Terminal, Users (owner/manager/cashier, PIN login via
  JWT), API keys (`tz_test_`/`tz_live_` prefixed) for server-to-server auth.
- Generic CRUD router (`app/crud_router.py`) backing branches, terminals, users, categories,
  products, modifier-groups (+ modifiers), deals, taxes, customers, floors (+ tables),
  kitchen-stations, payment-methods, orders, payments, webhooks, api-keys — all with
  `?limit&offset&updated_since` and company scoping.
- Orders: lines + per-line modifiers, discounts, order types (dine-in/takeaway/delivery),
  `kds_status` (new/preparing/done) for the kitchen display, `/pay` (cash/card/digital tender,
  split payments, change calc), `/void`, `/refund`, `/send-to-kitchen`, `/kds-status`.
- Offline sync: `POST /api/v1/sync/batch` upserts by `client_uuid` (idempotent — safe to
  resend), `GET /api/v1/sync/status` with synced/pending/failed counts and per-order
  server/fiscal/ERP status.
- Fiscal adapter interface (`app/adapters/fiscal/`): `MockFBRAdapter` (default, configurable
  failure rate via `FISCAL_MOCK_FAIL_RATE`) returns realistic
  `123456-DDMMYYHHMMSS-0001`-style invoice numbers; `FBRIMSAdapter` builds the real FBR IMS
  sandbox payload (unused unless `FISCAL_PROVIDER=fbr`).
- ERP adapter interface (`app/adapters/erp/`): `MockERPAdapter` (default) and an `OdooAdapter`
  skeleton (XML-RPC `execute_kw`, `product.product` + `pos.order.create_from_ui`, unused
  unless `ERP_PROVIDER=odoo`).
- Rs.1 POS fee added to every paid order; cash vs card/digital tax rates (PRA-style).
- Receipts: JSON (`GET /orders/{id}/receipt`) and an 80mm-styled HTML receipt
  (`/receipt.html`) with all SRO 1006 fields (NTN/STRN/tax breakdown/POS fee), FBR fiscal
  number, inline SVG QR, and the "Verify via FBR Tax Asaan / SMS 9966" line; offline-mode and
  fiscal-failed states get their own receipt badges.
- Shifts: open (cash float) / close (counted cash vs expected, over/short) / Z report
  (gross sales, tax, fees, by-payment-method breakdown, fiscal ok/failed counts).
- Webhooks: HMAC-SHA256 signed, best-effort delivery (`order.created/paid/voided/refunded`,
  `fiscal.succeeded/failed`, `sync.failed`).
- Demo seed (`app/seed.py`, runs on startup if empty): company "Lahore Karahi House"
  (Gulberg + DHA branches), PIN logins 1111/2222/3333, ~30 menu items, modifier groups, 2
  deals, 2 floors/14 tables, 5 payment methods, 4 kitchen stations, ~25 sample orders (3
  forced fiscal-failed, 2 ERP-pending), one open + one closed shift with a real Z report, and
  3 "client pending" carts exposed at `GET /api/v1/demo/unsynced-orders` for the web app to
  preload into IndexedDB.
- **Tests** (`api/tests/`, pytest + in-memory SQLite): 19 tests, all passing — CRUD +
  auth/company-scoping, sync-batch idempotency, pay (tax/fee/fiscal/ERP), void/refund,
  offline-order + fiscal-retry handling, receipt field checks (JSON + HTML), shift
  open/close + Z-report math.

### Frontend (`web/`)
Next.js 14 (App Router, TypeScript), Tailwind, built as a PWA (manifest + service worker
caching the app shell). Dark sidebar / light content cards, emerald + amber accents, large
touch targets, EN/UR toggle (`lib/lang.tsx`) covering nav/cart/pay/order-type labels.

Pages: `/login` (PIN pad + branch/terminal picker), `/pos` (categories, search, modifier
dialog, cart, order type/table/customer, Pay dialog with split tenders + change calc,
post-pay receipt view), `/tables` (floor plan, free/occupied), `/kds` (tickets by station,
Start/Done via the `kds-status` endpoint, auto-refresh), `/orders` + `/orders/[id]` (history,
filters, detail + receipt link), `/sync` (Synced/Pending/Failed counters, per-order chips,
Retry/Retry all, Simulate-offline toggle), `/shifts` (open/close/Z-report), `/admin`
(Products/Categories/Modifiers/Tables tabs + API Keys tab + link to `/api/docs`).

Offline-first: every order is written to IndexedDB (`lib/db.ts`, via `idb`) before any network
call; a background loop (`lib/sync.ts`, `components/SyncLoop.tsx`) pushes unsynced orders via
`/api/v1/sync/batch` every 10s when online, with an online/offline badge + pending count in
the header at all times.

`npm run build` passes cleanly (11 routes, zero errors).

### Infra & docs
- `docker-compose.yml`: `db` (Postgres 16), `api` (port 8000 internal), `web` (Next.js
  standalone build, port 3000 internal, proxies `/api/*` to `api`), host port
  `${APP_PORT:-8120}`. `.env.example` documents every variable.
- `.github/workflows/ci.yml`: pytest + `npm run build` on every push/PR.
- `docs/HOW_TO_TEST.md`, `docs/api-guide.md`, `postman/tezz.postman_collection.json`.
- `api/Dockerfile`, `web/Dockerfile` (multi-stage, standalone output).
- Postgres driver is `pg8000` (pure-Python, BSD-licensed) rather than `psycopg` (LGPL), to
  keep the dependency set MIT/Apache/BSD-only as required.

## How this was verified
- `cd api && pytest -q` → **19 passed**.
- `cd web && npm run build` → clean, zero errors.
- Manual end-to-end smoke test (outside docker, to work around a sandbox limitation — see
  below): ran the real `uvicorn` api against a fresh SQLite DB and the real Next.js
  production server side by side, then through the web app's own `/api/*` proxy: PIN login →
  fetched branches/terminals/products with the seeded demo key → created an order → paid it
  (tax + Rs.1 fee applied correctly) → fetched `/receipt.html` and confirmed a real FBR fiscal
  number, QR `<svg>`, and the Tax Asaan line were present.
- `docker build` succeeded for both `api/Dockerfile` and `web/Dockerfile`, and
  `docker compose up --build` created all three containers correctly (db reached "healthy").
  However, in this sandboxed build environment, **container-to-container networking on a
  custom Docker bridge network is blocked** (verified independently with two plain `alpine`
  containers on the same compose network — a bare `nc -z` between them times out), so the
  `api` container could not reach `db` and the full compose stack could not be exercised
  end-to-end here. The compose file, Dockerfiles, and env wiring are correct as far as this
  environment can confirm (images build, config validates, host-level equivalent flow works);
  please do a `docker compose up --build` smoke test in a normal (non-sandboxed) Docker
  environment before relying on it for a live demo.

## Known deviations / not done
- Real FBR IMS and Odoo adapters are implemented but not exercised against live
  endpoints/credentials (by design — no sandbox credentials were available; `FISCAL_PROVIDER`
  /`ERP_PROVIDER` env vars switch to them).
- PWA icons are hand-drawn SVGs, good enough for install/demo but not a full generated PNG
  icon set.
- ESLint is not build-blocking (`next.config.js` sets `eslint.ignoreDuringBuilds: true`) so
  `npm run build` fails only on real TypeScript/compile errors.
- WhatsApp receipt links and a few v1.1/v2 items from `docs-POS_PLAN.md` section 12 (dynamic
  QR payments, Foodpanda, loyalty) were out of scope for this v1 per the plan itself.

## How to run
See `README.md` for full instructions. Quick path:
```bash
docker compose up --build
# open http://localhost:${APP_PORT:-8120}
```
or run `api` and `web` locally without docker (also in `README.md`) — PIN logins 1111 (owner)
/ 2222 (manager) / 3333 (cashier).
