# Sync Test Report (Tezz POS v2)

Date: 2026-10-16 (Riyadh). Stack: Docker (Postgres 16, FastAPI, Next.js 14), Chromium via Playwright.
Fiscal adapter: mock FBR. ERP adapter: WAGS Odoo (CS staging) for the Odoo company, mock for the demo company.

## How to run

```bash
# Backend unit/integration tests (in-memory SQLite, no Docker needed)
cd api && pytest -q

# End-to-end tests against the running stack (needs the app on :8120 and Docker for DB checks)
pip install playwright pytest && python -m playwright install chromium
python -m pytest e2e/test_e2e_pos.py -v

# Opt-in staging test (writes ONE draft quotation to CS staging Odoo)
docker compose exec -e TEZZ_STAGING=1 api python -m pytest tests/test_staging_odoo.py -q -s
```

## Results summary

| Suite | Result |
|---|---|
| Backend pytest (`api/tests`) | 45 passed, 1 skipped (staging test is opt-in) |
| End-to-end Playwright (`e2e/test_e2e_pos.py`) | 10 passed |
| Staging Odoo integration (`api/tests/test_staging_odoo.py`) | 1 passed (run once) |

## Scenarios

| # | Scenario | How it is tested | Result |
|---|---|---|---|
| 1 | Online order, paid once | e2e `test_delivery_order`, pytest `test_pay_fiscal` | Pass |
| 2 | Offline order, then automatic sync when back online (no Retry click) | e2e `test_offline_order_syncs_automatically` (browser network set offline, then online) | Pass. Order reaches server once, is paid, FBR status ok, `offline=true` kept |
| 3 | Sync Status page shows not-synced rows offline, synced after reconnect | Same test, screenshots 06 and 07 | Pass |
| 4 | Double-click on Confirm payment | e2e `test_double_click_pay_creates_one_order` | Pass. 1 order, 1 payment |
| 5 | Network drops between "create order" and "pay" | e2e `test_drop_between_create_and_pay` (first `/pay` aborted) | Pass. Order finalized by the sync loop, 1 payment |
| 6 | Server processed the payment but the response was lost | e2e `test_lost_pay_response_no_double_charge` | Pass. Client re-reads the order, 1 payment, FBR called once |
| 7 | Two tabs offline, both sell, reconnect | e2e `test_multi_tab_offline_then_reconnect` | Pass. Each order exactly once (Web Locks: one tab syncs at a time) |
| 8 | Tab closed during a sync request (crash mid-sync) | e2e `test_crash_mid_sync_recovers` (batch request hangs, page closed, new page opened) | Pass. Stale "SYNCING" row picked up again, 1 order, 1 payment |
| 9 | Parked orders survive reload and work offline | e2e `test_park_switch_and_reload` | Pass |
| 10 | Two requests pay the same order at the same instant | pytest `test_parallel_pay_threads_only_one_wins` | Pass. One wins, the other gets 400, FBR called once |
| 11 | Same client_uuid sent twice (POST and sync batch, and twice in one batch) | pytest `test_double_submit_same_uuid_creates_one_order` | Pass |
| 12 | Another worker is already sending to FBR / order already fiscalized | pytest `test_claim_blocks_concurrent_sender` | Pass. No duplicate FBR invoice |
| 13 | FBR down: automatic server retry with backoff, then success, never resent | pytest `test_auto_retry_with_backoff_then_success` | Pass (30s, 60s, ... max 1h) |
| 14 | API process crashed while sending to FBR | pytest `test_crash_mid_send_is_recovered` | Pass. "sending" older than 5 min is retried |
| 15 | Order made offline is fiscalized when it reaches the server | pytest `test_offline_order_is_fiscalized_on_sync` | Pass |
| 16 | Blank/stale terminal, user, table ids from an offline device | pytest `test_blank_or_stale_refs_do_not_block_sync` | Pass (was a bug, see below) |
| 17 | Order pushed to Odoo twice (retry/reconnect) | staging `test_push_twice_creates_one_draft_quotation`, pytest `test_push_creates_draft_quotation_once` | Pass. One draft quotation |
| 18 | Company data isolation | pytest `test_company_isolation` | Pass |
| 19 | Delivery fee in totals, tax, receipt, FBR and Odoo payloads | pytest delivery tests, e2e `test_delivery_order` | Pass |
| 20 | Product images (upload, serve, delete, Odoo import, no overwrite of uploads) | pytest image/import tests, e2e `test_product_images_and_placeholder` | Pass |

## Bugs found and fixed

1. **One bad order blocked the whole sync queue.** A cashier who logged in without picking a terminal and then went offline
   produced orders with `terminal_id=""`. The sync batch failed with HTTP 500 and every queued order on that device stayed
   unsynced forever. Fix: blank or unknown optional references are cleared on the server, and each order in a batch is
   processed on its own (one failure no longer fails the rest).
2. **Stuck "SYNCING" after a crash.** If the tab closed during a sync, rows stayed "SYNCING" and were never retried.
   Fix: rows older than 2 minutes in that state are retried.
3. **Payment never finalized after a network drop.** If the order was created but the pay call failed during sync,
   the row was marked SYNCED with the order still open. Fix: it stays due and is retried until paid.
4. **Double charge risk.** Paying the same order twice in parallel could create two payments and two FBR invoices.
   Fix: atomic compare-and-set on the order status ("open" to "paying"), and on FBR/Odoo status ("sending").
5. **Double-click created two orders.** A new client_uuid was generated on each confirm. Fix: each open order has a
   fixed id from the start, plus an in-flight guard on the Pay button.
6. **FBR needed manual Retry.** Fix: background worker in the API retries FBR and Odoo with exponential backoff;
   the browser also retries failed uploads automatically (5s doubling to 5 min) and immediately on reconnect.
7. **Offline orders were never fiscalized** (they stayed "offline_mode"). Fix: they are sent to FBR when they reach the server.
8. **Only 200 products loaded.** The Odoo company has 420 POS products; the cashier screen loaded only the first page.
   Fix: all pages are loaded.
9. **Products and other lists were reloaded on every screen update** (effect depended on a new session object each render).
   Fix: depend on the session token.
10. **Company data isolation.** Companies, terminals, modifiers, floors, tables and payments could be listed or edited
    with another company's API key; orders could be created on another company's branch. Fix: all scoped to the caller's company.
11. **'Gift Card Product' imported from Odoo.** It is not flagged as a gift voucher in WAGS. Fix: excluded by name and deactivated.

## Staging records created (CS staging Odoo, for cleanup)

| Model | id | Name | client_order_ref | State |
|---|---|---|---|---|
| sale.order.wags | 42421 | QU40806 | TEZZ-TEST-SYNC-e663790e58 | draft |

Earlier records from 2026-10-15 (T5) are still there: QU40803 (42418), QU40804 (42419), QU40805 (42420), all draft and labelled TEZZ-TEST.
No pos.wags records were created. Nothing was confirmed. Nothing was sent to ZATCA.
The Odoo product import is read-only.

## Known limits

- FBR: if FBR accepted an invoice but the response was lost, a later automatic retry sends the same USIN again.
  We rely on FBR rejecting duplicate USINs. This must be confirmed with the real FBR sandbox (no credentials yet).
- Two tabs on the same device share the open-orders list. Two cashiers should use two devices or two browser profiles.
- e2e tests run against the demo company with the mock fiscal adapter. The real FBR adapter is not tested end to end.
