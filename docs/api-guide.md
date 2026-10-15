# Tezz POS API guide — integrate in 15 minutes

Full interactive reference: `GET /api/docs` (Swagger) or `/api/redoc`. OpenAPI JSON at
`/api/openapi.json`. This guide covers the common integration path with curl.

All requests need `Authorization: Bearer <token>`. Two kinds of token:
- **API key** (`tz_test_...`), per company, for server-to-server integration (ERPs,
  WhatsApp bots, accounting). Create one from `/admin` -> API Keys, or `POST /api/v1/api-keys`.
- **User JWT**, from `POST /api/v1/auth/login`, for the cashier PWA.

## 1. List your menu
```bash
curl -s $BASE/api/v1/products -H "Authorization: Bearer $API_KEY" | jq
curl -s $BASE/api/v1/categories -H "Authorization: Bearer $API_KEY" | jq
curl -s $BASE/api/v1/modifier-groups -H "Authorization: Bearer $API_KEY" | jq
curl -s $BASE/api/v1/deals -H "Authorization: Bearer $API_KEY" | jq
```
Poll with `?updated_since=2026-10-15T00:00:00` to pull only changes (e.g. for a WhatsApp
bot keeping its menu in sync).

## 2. Create an order (e.g. from a WhatsApp bot)
```bash
curl -s -X POST $BASE/api/v1/orders -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{
  "client_uuid": "wa-'"$(uuidgen)"'",
  "branch_id": "'"$BRANCH_ID"'",
  "order_type": "delivery",
  "source": "whatsapp",
  "lines": [
    {"product_id": "'"$PRODUCT_ID"'", "name_snapshot": "Chicken Biryani", "qty": 2, "unit_price": 450}
  ]
}' | jq
```
`client_uuid` is your idempotency key — safe to retry the exact same request.

## 3. Take payment
```bash
curl -s -X POST $BASE/api/v1/orders/$ORDER_ID/pay -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{
  "payments": [{"payment_method_id": "'"$CASH_PM_ID"'", "amount": 945, "tendered": 1000}]
}' | jq
```
The response includes `fiscal_number`, `fiscal_status`, `erp_status`. Fetch the printable
receipt with `GET /api/v1/orders/$ORDER_ID/receipt.html`.

## 4. Offline sync batch (what the PWA does)
```bash
curl -s -X POST $BASE/api/v1/sync/batch -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{
  "terminal_id": "'"$TERMINAL_ID"'",
  "orders": [ { "client_uuid": "...", "branch_id": "...", "lines": [...] } ]
}' | jq
curl -s "$BASE/api/v1/sync/status?terminal_id=$TERMINAL_ID" -H "Authorization: Bearer $API_KEY" | jq
```

## 5. Retry a failed fiscal/ERP push
```bash
curl -s -X POST $BASE/api/v1/fiscal/$ORDER_ID/retry -H "Authorization: Bearer $API_KEY"
curl -s -X POST $BASE/api/v1/erp/$ORDER_ID/retry -H "Authorization: Bearer $API_KEY"
```

## 6. Webhooks
Subscribe:
```bash
curl -s -X POST $BASE/api/v1/webhooks -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{
  "url": "https://your-server.example/webhooks/tezz",
  "secret": "whsec_your_shared_secret",
  "events": "order.paid,fiscal.failed"
}'
```
Events: `order.created`, `order.paid`, `order.voided`, `order.refunded`, `fiscal.succeeded`,
`fiscal.failed`, `sync.failed`. Each delivery is an HMAC-SHA256-signed POST:
- Header `X-Tezz-Signature`: hex HMAC-SHA256 of the raw request body, keyed with your `secret`.
- Header `X-Tezz-Event`: the event name.
- Body: `{"event": "order.paid", "data": {...}}`.

Verify in Python:
```python
import hmac, hashlib
expected = hmac.new(secret.encode(), request_body_bytes, hashlib.sha256).hexdigest()
assert hmac.compare_digest(expected, request.headers["X-Tezz-Signature"])
```
Delivery is best-effort (no automatic retry queue in v1) — if your endpoint is down,
check `GET /api/v1/fiscal/status` / `/api/v1/erp/status` and poll `GET /api/v1/orders`
with `?updated_since=` as a fallback.

## Sample code
- **curl**: see above.
- **Python**: `requests.post(f"{BASE}/api/v1/orders", json=payload, headers={"Authorization": f"Bearer {API_KEY}"})`.
- **JS**: `fetch(`${BASE}/api/v1/orders`, {method: "POST", headers: {Authorization: `Bearer ${API_KEY}`, "Content-Type": "application/json"}, body: JSON.stringify(payload)})`.

## Sandbox
The seeded demo company ("Lahore Karahi House") and its sandbox API key work as a test
tenant out of the box — see `/admin` -> API Keys in the running app, or `SUMMARY.md`.
