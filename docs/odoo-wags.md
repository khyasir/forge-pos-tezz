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
- v2 import also brings: product image (`image`, served at `/api/v1/products/{id}/image`; an image uploaded in Tezz
  admin is never overwritten), variant attributes from `product.attribute.line.wags` (shown as "Attr: Value" under the
  product name), and it excludes "Gift Card Product". Products no longer available in POS are deactivated.
  WAGS combos (`is_combo`) exist as a field but no POS product on staging uses them (0 found), so none are imported.
  On staging: 420 products, 66 with images, 88 with attributes, 7 modifier groups / 44 modifiers.
- Push (Tezz -> Odoo): each paid order becomes a `sale.order.wags` **in Draft (Quotation)** on branch.wags
  ODOO_BRANCH_ID (default 24 = "Test"), `client_order_ref` = our USIN (idempotent: searched before create),
  notes start with "TEZZ-TEST". The note also carries the order type, delivery fee and delivery address.
  Set ODOO_DELIVERY_PRODUCT_ID to add the delivery fee as its own quotation line.
  Failed pushes are retried automatically by the API (exponential backoff, max 1 hour).

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
