# POS_PLAN.md: "Tezz POS" (brand chosen by ATLAS; "tezz" = fast in Urdu), Pakistan-first restaurant/retail POS
Status: PLAN ONLY, not building yet. Written 2026-10-15 by ATLAS.
Note: this is far bigger than the 3-day studio rule (Hard rule 4). Treat it as a multi-week project with 3-day milestones.

## 0. One-line promise
A fast, FBR-ready POS for Pakistani restaurants and shops that plugs into the ERP you already use (Odoo first).

## 1. Who buys and why
- Tier-1 retailers and restaurants in Pakistan that MUST report every sale to FBR in real time and print the FBR number + QR on receipts (FBR POS booklet: https://download1.fbr.gov.pk/Docs/202551615541769POSBooklet.pdf).
- Restaurants in Sindh/Punjab that must integrate with SRB/PRA (SRB FAQ: https://www.srb.gos.pk/srb/faq/ ; PRA spec: https://e.pra.punjab.gov.pk/templates/Technical_Specification_Software_Fiscal_Device_1.2_PRA.pdf).
- Businesses already on Odoo 16 (Camel Step/WAGS-type clients) who want a better cashier screen than Odoo POS but keep Odoo as the books.

## 2. Features v1 (plain words)
1. Cashier screen: big buttons, categories, search, barcode scan, hold/recall order, discounts, split bill.
2. Modifiers: "extra cheese", "no onion", sizes, combos, with price changes.
3. Tables: floor plan, open table, move/merge tables, waiter name, dine-in/takeaway/delivery.
4. Kitchen display (KDS): orders appear on a kitchen screen by station, "start" and "done" buttons, kitchen ticket print as backup.
5. Payments: cash (with change), card (manual), JazzCash/Easypaisa/bank QR as manual tender types; multiple payments per bill.
6. Shifts: open with cash float, close with counted cash, over/short, Z report (day/week/month closing is legally required, see booklet rule (f)).
7. Offline: cashier keeps selling without internet (browser storage), invoices marked "offline mode", auto-sent to FBR within 24h of reconnect (rule 150XC).
8. Receipts: thermal 80mm print with all SRO 1006 fields, FBR invoice number, FBR POS logo, 7x7mm QR, Rs.1 POS fee line, "Verify via Tax Asaan / SMS 9966" text.
9. Back office: products, prices, taxes (per item rate + PCT code), users/roles (cashier, manager), branches, basic sales reports.
Non-goals v1: inventory recipes, loyalty, delivery aggregator integration (Foodpanda), own payment gateway, mobile apps (PWA only), accounting (ERP does it).

## 3. Stack
- Frontend: Next.js (React) PWA with offline storage (IndexedDB) + service worker. Works on tablet, PC, Android browser.
- Backend: Python FastAPI, Postgres, background worker (RQ or a simple DB-queue) for FBR and ERP sync with retries.
- Print: browser print to 80mm thermal (ESC/POS via local print helper later).
- Docker compose: web, api, worker, db. APP_PORT from env. All MIT/Apache/BSD deps.

## 4. Architecture (adapter layer)
```
[Cashier PWA]--(offline queue)-->[POS API (FastAPI)]--+--> [Fiscal adapter]  FBR IMS | PRA | SRB | FBR DI (later)
                                       |              |
                                  [Postgres]          +--> [ERP adapter]  Odoo16 (JSON-RPC) | Generic REST (webhooks) | None
```
- Our own Postgres is the source of truth for orders while selling. ERP and tax authority are "outputs" via adapters.
- Each adapter implements: pull_products(), pull_customers(), push_order(order), push_refund(order), health().
- Fiscal adapter implements: fiscalize(invoice) -> {fiscal_number, qr_payload}, retry_pending().
- Every outbound call is idempotent (we key on our USIN) and logged with request + response.

## 5. FBR flow (findings, with links)
FBR POS (IMS, Tier-1 retailers):
- Sandbox: POST https://esp.fbr.gov.pk:8244/FBR/v1/api/Live/PostData ; Production: POST https://gw.fbr.gov.pk/imsp/v1/api/Live/PostData ; Bearer token. Source: https://github.com/Tier3-Pk/FBR-POS-INTEGRATION-SERVICES/blob/main/FBR%20integration%20with%20Cloud%20Based%20POS%20-%20Using%20WEBAPI.txt
- Alternative local mode: FBR/PRA "software fiscal device" Windows service at http://localhost:8524/api/IMSFiscal/GetInvoiceNumberByModel (https://forum.sambapos.com/uploads/short-url/XSMFnYCsTOJs1Nib2O2MNLTbUk.pdf). We use cloud mode (no Windows dependency).
- Invoice JSON fields: InvoiceNumber (blank), POSID (from FBR registration), USIN (our unique invoice id), DateTime, BuyerNTN, BuyerCNIC, BuyerName, BuyerPhoneNumber, TotalBillAmount, TotalQuantity, TotalSaleValue, TotalTaxCharged, Discount, FurtherTax, PaymentMode (1 cash, 2 card, ...), RefUSIN (for returns), InvoiceType (1 sale, 3 return per common usage; verify in sandbox), Items[ItemCode, ItemName, Quantity, PCTCode, TaxRate, SaleValue, TotalAmount, TaxCharged, Discount, FurtherTax, InvoiceType, RefUSIN]. Source: https://github.com/Tier3-Pk/FBR-POS-INTEGRATION-SERVICES/blob/main/Sample%20JSON%20Format%20for%20FBR%20IMS%20Component.txt
- Success: Code "100" + InvoiceNumber. Store it, never repost; a timeout is ambiguous, reconcile before retry. Source: https://github.com/marslankhalid/fbr-ims-laravel
- Receipt must show (SRO 1006(I)/2021, https://download1.fbr.gov.pk/SROs/202189168291729SRO-1006.pdf): business name, address, STRN, NTN, tax office, POS registration number; sequential invoice no., date/time, payment mode; item-wise price excl. tax, tax rate, qty; tax amount, total sale value, discount, POS service fee Re.1, payable, received; FBR fiscal number (format XXXXXX-DDMMYYHHMMSS-0001), FBR POS logo, 7x7mm QR, "Verify this invoice through FBR Tax Asaan Mobile App or SMS at 9966 and win exciting prizes in draw".
- Rs.1 POS service fee per invoice, collected by Tier-1 retailer, deposited with monthly sales tax return (SRO 1279(I)/2021). Listed at https://www.fbr.gov.pk/pos-legal-provisions/163085/163086 . Our POS adds it as a separate line, outside taxable value.
- Offline: invoices made during internet/power failure must be marked "offline mode" and uploaded within 24 hours of restoration (Rule 150XC, booklet above).
- Also required: day/week/month closing, logs of every edit/cancel, encrypted irrevocable storage, outlet signboard "Integrated with FBR" (booklet above).
- Registration (high level, to confirm with Yasir/client): retailer registers outlets and POS machines on FBR IRIS, gets POSID per terminal + token; test in sandbox; FBR/PRAL whitelists; then production token. Exact screens need the client's IRIS login.

FBR Digital Invoicing (DI) API (B2B sales tax invoices, SRO 69(I)/2025):
- Sandbox https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata_sb , Production .../postinvoicedata, plus validateinvoicedata and reference lookups (HS codes, UoM, provinces, SRO). Token from IRIS, valid 5 years; scenario tests in sandbox unlock production. Sources: https://download1.fbr.gov.pk/Docs/20257301172130815TechnicalDocumentationforDIAPIV1.12.pdf , https://download1.fbr.gov.pk/Docs/20256251162757102DIUserManualV1.4.pdf
- Relevance: needed for B2B invoices (e.g. corporate catering, wholesale). Plan as v2 adapter; same adapter interface.

Provincial:
- PRA (Punjab): register each branch POS on PRA portal, use PRA fiscal device or cloud PostData; cloud prod https://ims.pral.com.pk/ims/production/api/Live/PostData with Bearer + IP whitelisting; print PRA number + QR. Source: https://e.pra.punjab.gov.pk/templates/Technical_Specification_Software_Fiscal_Device_1.2_PRA.pdf , manual https://e.pra.punjab.gov.pk/templates/POS_COMPONENT_and_eIMS_User_Manual.pdf
- SRB (Sindh): mandatory for restaurants in hotels, franchises, multi-branch, AC malls, online marketplace, or turnover > Rs.5m (https://www.srb.gos.pk/srb/faq/). Tax 15% cash, 8% on card/wallet/QR unless restaurant is on List A (https://www.srb.gos.pk/srb/other-services/). Cloud integration tech doc on https://www.srb.gos.pk/srb/point-of-sale-pos/ (need to download and read; not yet parsed).
- So restaurants mostly report to the PROVINCE (services tax), retail shops to FBR. v1 must support FBR + PRA; SRB in M4.

## 6. Odoo 16 adapter
- External API: JSON-RPC /jsonrpc or XML-RPC, execute_kw with db, uid, API key. Docs: https://www.odoo.com/documentation/16.0/developer/reference/external_api.html
- Products: search_read product.product (available_in_pos, list_price, taxes_id, barcode, pos_categ_id). Customers: res.partner.
- Orders, two options:
  A) pos.order via create_from_ui. Needs a pos.config per branch and an OPEN pos.session; the adapter opens one per day and closes it at Z report, which posts accounting entries in Odoo. Sources: https://odoo-development.readthedocs.io/en/latest/dev/pos/send-pos-orders-to-server.html , https://github.com/odoo/odoo/blob/16.0/addons/point_of_sale/models/pos_order.py
  B) sale.order + confirm + account.move invoice. No pos.config needed, simpler, but Odoo POS reports stay empty.
  Decision: default A (pos.config "External POS - <branch>"), fallback B by setting. Verify payload on CS staging first.
- Map: our tax codes -> account.tax ids; our payment types -> pos.payment.method ids. Store FBR number in pos.order note / custom field (x_fbr_invoice_no) if allowed.

## 7. Generic REST API (for any ERP), OpenAPI at /docs and /openapi.json
- POST /api/v1/auth/token (API key -> JWT)
- GET/POST/PATCH /api/v1/products, /api/v1/categories, /api/v1/modifiers
- GET/POST /api/v1/customers
- GET/POST /api/v1/branches, /api/v1/terminals
- POST /api/v1/orders (create, idempotency-key), GET /api/v1/orders?since=
- POST /api/v1/orders/{id}/pay, /refund, /void
- GET /api/v1/orders/{id}/receipt (JSON + HTML)
- POST/GET /api/v1/shifts (open/close), GET /api/v1/reports/z?shift=
- GET /api/v1/fiscal/status, POST /api/v1/fiscal/retry
- POST /api/v1/sync/products (bulk upsert from ERP)
- Webhooks out: order.paid, order.refunded, shift.closed, fiscal.failed (HMAC-signed)
Docs plan: FastAPI auto OpenAPI + Redoc page, plus docs/integration-guide.md with curl examples and a Postman collection.

## 8. Milestones (working days, ~6h each)
- M1 (3d): data model, products/orders API, cashier screen basic, receipt print, docker compose.
- M2 (3d): FBR IMS sandbox adapter, USIN/idempotency, QR + logo receipt, Rs.1 fee, offline queue + 24h upload, logs.
- M3 (3d): Odoo 16 adapter on CS staging (products pull, pos.order push, session open/close).
- M4 (3d): modifiers, tables, KDS, shifts + Z report, PRA adapter.
- M5 (3d): generic REST docs, webhooks, roles, QA, landing + pricing. SRB adapter if docs allow.
Total about 15 working days to a pilot. Pilot at 1 real outlet before selling.

## 9. Pricing (Pakistan, PKR)
Competitors:
- Bhookly Rs.10,000/mo Starter, Rs.15,000 Growth, fiscal included, no setup fee: https://bhookly.com/resources/blog/restaurant-pos-price-pakistan-2026
- Granet Pro Rs.2,999/mo per branch + Rs.50,000 setup + Rs.2,000/mo PRA/FBR add-on (same source)
- Oscar POS ~Rs.4,000/mo (third-party figure, not on Oscar site), FBR included: same source + https://oscar.pk/blog/fbr-pos-integration-with-oscar-make-your-business-compliant
- Foodics (KSA) SAR 423 / 801 / 1,224 per month bundles: https://www.foodics.com/pricing/ (not sold in Pakistan as far as found)
Our proposal:
- Starter Rs.4,999/mo per branch (1 terminal, FBR or PRA included, KDS, offline).
- Pro Rs.8,999/mo per branch (3 terminals, tables, modifiers, reports, 2 provinces).
- ERP connector (Odoo or REST webhooks) +Rs.3,000/mo per company.
- Setup and menu load: Rs.15,000 one-time (waived on annual).
- Annual = 2 months free.

## 10. Risks
- Legal/licensing: FBR may require POS software vendors to be licensed/registered integrators (SRO 69(I)/2025 talks about licensing). Must confirm before selling. Escalate to Yasir.
- Tax rules change often (rates, SRB 8%/15%, formats). Keep rules in config, not code.
- Offline + fiscal: duplicate posting if timeouts; solved by USIN idempotency and reconcile step.
- Odoo session handling (pos.session must be open) and customizations on WAGS/Camel Step DB.
- Scope: much larger than studio 3-day rule; risk of never shipping. Mitigation: pilot one outlet after M2+M3.
- Hardware: thermal printers, cash drawers vary; start with browser print.
- Competitors already include FBR at Rs.3-10k; our edge is ERP/Odoo connector + clean UX.

## 11. What Yasir must provide
1. CS staging Odoo 16: URL, database name, API user login + API key (not admin), and which company/branch to use. Permission to create a pos.config "External POS".
2. FBR IMS sandbox: POSID + sandbox token (from client IRIS), and NTN/STRN of the test business.
3. PRA sandbox POS ID/token if first client is in Punjab; SRB cloud integration doc/credentials if Sindh.
4. A real pilot outlet (restaurant or shop), province, and current tax rates they charge.
5. Confirmation on legal side: are we allowed to sell as POS software vendor, or do we partner with a licensed integrator (PRAL offers free integrator services).
6. Brand name decision and a sample receipt printer model.

---
# UPGRADE 2026-10-15 (business-owner view). Overrides earlier sections where they conflict.
Legend: [V] verified from the linked page today. [U] unverified / third-party / inferred.

## 12. Revised v1 feature list
Must (v1):
1. Offline-first cashier: every order saved on the device first (IndexedDB), works through loadshedding/internet cuts, syncs later. [V need: Granet/Oscar both sell this as headline https://www.granetpro.com/pos-software-in-pakistan.html , https://oscar.pk/solutions/restaurant-solutions]
2. Sync Status page: list of orders Synced / Pending / Failed per device, with reason, "Retry" and "Retry all", and separate columns for Server, FBR/PRA, ERP.
3. Cashier: categories, search, barcode, modifiers, deals/combos (Pakistan "deals" culture [U]), discounts, split bill, hold/recall.
4. Dine-in/takeaway/delivery, tables, waiter.
5. KOT printing auto-routed by station + KDS screen [V Oscar/Granet pages above].
6. Payments: cash, card, Raast QR / JazzCash / Easypaisa as tender types (manual confirm v1; dynamic QR v2) [V JazzCash Raast QR https://www.jazzcash.com.pk/business/accept-payments/qr-raast-payments ; Easypaisa fees 1% https://easypaisa.com.pk/online-payment-gateway/].
7. Shifts, cash float, Z report (day/week/month closing legally required).
8. FBR/PRA fiscal adapter (mock first), receipts with fiscal no + QR + Re.1 fee, offline-mode label and 24h upload.
9. WhatsApp receipt link (send receipt URL via partner or wa.me link) [U demand; Oscar mentions "WhatsApp follow-ups"].
10. Urdu + English UI and receipts [U demand, but common in competitor marketing https://pos.arriverr.com/integrations].
11. Multi-branch hierarchy: Company > Brand > Branch > Terminal > Shift/Session.
v1.1: Foodpanda plugin (needs Delivery Hero partner approval [V https://integration.foodpanda.com/en/how-it-works/ , https://developers.deliveryhero.com/documentation/pos.html]), inventory + recipes, loyalty, owner mobile dashboard.

## 13. Offline sync design
- Each terminal has a device id. Each order gets a client UUID (idempotency key) + local sequence number on creation, stored in IndexedDB with status: LOCAL -> SYNCING -> SYNCED | FAILED(reason, attempts).
- Background sync loop: every 10 s when online (navigator.onLine + /health ping), push oldest first via POST /api/v1/sync/batch (up to 50). Server upserts by client UUID, so resends are safe.
- Server tracks per-order downstream status: fiscal_status (pending/ok/failed/offline_mode) and erp_status. Workers retry with backoff (1m, 5m, 15m, 1h) and alert if the 24h FBR window is near.
- Conflicts: orders are append-only after payment; edits after sync become refund/void documents (required by FBR log rules).
- Products/prices pulled down to device on login and every 15 min (ETag), so selling works offline.
- Sync Status page (cashier + manager): counters (Synced / Pending / Failed), table with order no, time, amount, server/fiscal/ERP status chips, last error, Retry button, Retry all, export CSV. Manager can see all terminals of a branch.

## 14. Full public REST API (v1), all JSON, OpenAPI 3 at /docs and /openapi.json
Auth: API keys per company (scopes read/write, sandbox vs live prefix tz_test_ / tz_live_), plus user JWT for the PWA. Idempotency-Key header on all POST. Cursor pagination (?limit&cursor), filters (?updated_since). Errors: RFC 7807 style.
CRUD (GET list, GET one, POST, PATCH, DELETE) for:
companies, brands, branches, terminals, users, roles, categories, products, product-variants, modifier-groups, modifiers, deals (combos), price-lists, taxes, customers, tables, floors, kitchen-stations, payment-methods, orders, order-lines, payments, refunds, shifts (pos sessions), cash-movements, discounts, webhooks, api-keys.
Actions: POST /orders/{id}/pay, /void, /refund, /send-to-kitchen; POST /shifts/{id}/close; GET /shifts/{id}/z-report; GET /orders/{id}/receipt(.html|.pdf); POST /sync/batch; GET /sync/status; POST /fiscal/{order_id}/retry; GET /fiscal/status; GET /reports/sales.
Webhooks (HMAC-SHA256 signed, retries): order.created, order.paid, order.refunded, order.voided, shift.closed, product.updated, fiscal.succeeded, fiscal.failed, sync.failed.
Docs deliverables: Redoc site, "Integrate in 15 minutes" guide, recipes (ERP sync, WhatsApp order injection, e-commerce), Postman collection, sample code (curl, Python, JS), sandbox tenant with test data and mock FBR.

## 15. Business view
Target segments (in order):
1. Single and 2-5 branch restaurants/cafes in Lahore, Islamabad/Rawalpindi, Karachi that must be PRA/SRB/FBR integrated (SRB rules: https://www.srb.gos.pk/srb/faq/ [V]).
2. Odoo users (via WAGS/Camel Step network) wanting a better front counter.
3. Tier-1 retail shops (FBR POS mandatory) later.
Why customers switch POS [U, inferred from competitor marketing and general reviews; need interviews]: offline failures during loadshedding, slow support, hidden setup fees (e.g. Granet Rs.50,000 setup + compliance add-on, Bhookly blog https://bhookly.com/resources/blog/restaurant-pos-price-pakistan-2026 [U third-party]), no ERP link, separate tablets for Foodpanda.
Differentiators:
1. Visible sync truth: the Sync Status page proves no order was lost (others say "syncs automatically" but do not show it [U]).
2. Open public API + webhooks + sandbox from day 1, so ERPs, WhatsApp bots and accountants can plug in. Most PK POS do not publish APIs [U].
3. Odoo 16 connector out of the box.
4. Compliance included at every tier (FBR/PRA/SRB), no add-on fee.
5. Transparent PKR pricing, no setup fee, month-to-month, 14-day free trial.
6. Premium, fast UI in Urdu + English, works on cheap Android tablets.
GTM:
- Founder-led sales in 1 city first (Lahore or Islamabad), WhatsApp demos, 14-day trial, free menu loading.
- Resellers: hardware shops selling thermal printers/tablets bundle (20% recurring) [U].
- Accountants/tax consultants who handle FBR/PRA registration as referrers (Rs.5,000 per paid branch) [U].
- Partners: WhatsApp-bot companies (see section 16), Odoo partners.
- Content: Urdu YouTube shorts "FBR POS integration kaise karein", SEO pages on FBR/PRA/SRB compliance.
Revenue model: subscription per branch (Starter Rs.4,999, Pro Rs.8,999), ERP connector Rs.3,000/company, API access free on Pro, hardware bundles at small margin, paid onboarding for chains. Payment fees are not ours v1.
First 10 customers plan:
1. Yasir's network: WAGS/Camel Step Odoo clients (target 2-3).
2. 30 restaurants in one city via WhatsApp/visits with a 1-page compliance pitch (target 4).
3. 2 hardware resellers bundle (target 2).
4. 1 WhatsApp-bot partner (Aflatoon) cross-sell (target 1-2).
Offer: first 10 get 3 months at 50% for feedback calls and a testimonial.

## 16. Partner / reseller channel: Aflatoon AI
Who they are: WhatsApp AI "front desk" for Pakistani businesses: takes orders and bookings in Urdu/English, payments and rider dispatch, CRM, Meta-approved templates and campaigns. Pricing Starter Rs.19,999/mo (100 orders), Growth Rs.39,999/mo, Pro custom with "Custom API & webhooks". Source: https://aflatoon.ai [V fetched today]. Islamabad, 1-10 people, co-founder Maaz Gul: https://linkedin.com/company/aflatoon-ai [U, LinkedIn data via search]. Prices also listed at https://omatechstudio.com/best-ai-receptionist-pakistan [U third-party].
Fit: they own the WhatsApp channel; we own the counter, kitchen and tax compliance. Their WhatsApp orders today land in their own dashboard, not in a POS/kitchen/FBR flow [U, inferred from site].
Integration via our API:
- Aflatoon bot -> POST /api/v1/orders (source=whatsapp, channel_ref=chat id) -> KOT/KDS + fiscal + receipt.
- Our webhooks order.paid / fiscal.succeeded -> Aflatoon sends WhatsApp receipt (PDF/link with FBR QR) via approved utility template.
- Menu sync: Aflatoon pulls GET /products, /modifier-groups, /deals with updated_since, so prices match the POS.
- Status: order.status_changed (preparing/ready/out-for-delivery) -> Aflatoon messages customer.
Commercial options:
A) Referral: 20% recurring of POS fee for 12 months for each referred branch.
B) Reseller: they buy at 40% off list and set their own price/bundle ("Aflatoon + POS" bundle).
C) White-label: our POS under their brand, their logo/colours/domain, Rs.2,500 per branch/month floor fee to us, min 20 branches; they do first-line support, we do L2.
Recommended start: A + free integration support, move to B/C after 10 shared customers.
Pitch to them (short): "Your bot takes the order; we make it a real kitchen ticket, an FBR/PRA-compliant receipt, and an Odoo entry. Your customers get one stack, you get recurring revenue and stickier accounts. Free sandbox and API keys today."
Risks: they are very small (1-10 people) [U]; overlap if they build their own POS; dependency on Meta WhatsApp policy.
