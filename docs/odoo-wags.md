# Odoo 16 (WAGS / Camel Step) connector

Tested against CS staging (https://stepstaging.wags.sa, Odoo 16.0 with WAGS custom modules).
WAGS replaces standard Odoo models: products are `product.product.wags`, POS categories `pos.product.category.wags`,
modifiers `pos.product.modifier.wags`, taxes `account.tax.wags`, POS orders `pos.wags`, quotations `sale.order.wags`.
There is no standard `pos.config` / `pos.order` / `product.product`.

## What syncs
- Import (Odoo -> Tezz): POS categories, sale taxes, modifier categories + modifiers, POS products
  (active, available_in_pos, not modifier, not gift voucher; limit ODOO_IMPORT_LIMIT=500), customers with mobile
  (limit ODOO_CUSTOMER_LIMIT=200). Upsert by Odoo id (`erp_ref`), so re-running is safe.
  Imported into a separate Tezz company "Camel Step (Odoo staging)", branch "Odoo Test Branch", manager PIN 4444.
- Push (Tezz -> Odoo): each paid order becomes a `sale.order.wags` **in Draft (Quotation)** on branch.wags
  ODOO_BRANCH_ID (default 24 = "Test"), `client_order_ref` = our USIN (idempotent: searched before create),
  notes start with "TEZZ-TEST".

## Safety
- We never create `pos.wags` (it carries ZATCA signing/reporting fields) and never confirm, invoice or validate.
  Nothing is sent to ZATCA.
- The adapter refuses any URL without "staging" unless ODOO_ALLOW_PRODUCTION=1.
- Credentials only from an untracked env file. Never commit it.

## Setup
Create `.env.odoo` next to docker-compose.yml (gitignored):
```
ERP_PROVIDER=odoo_wags
ODOO_URL=https://stepstaging.wags.sa
ODOO_DB=step_live_erp_2
ODOO_USERNAME=admin
ODOO_PASSWORD=<from Yasir, never commit>
ODOO_BRANCH_ID=24
```
Then `docker compose up -d --build` and import:
`docker compose exec api python -m app.erp_import_cli`  (or `POST /api/v1/erp/import` as owner/manager).

## Known limits
- Draft quotation line totals show 0 until opened/recomputed in Odoo (WAGS computes them in the UI onchange).
- Imported prices are Odoo `pos_price` (SAR, may be VAT-inclusive). Currency is not converted.
