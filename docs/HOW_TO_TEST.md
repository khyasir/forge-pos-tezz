# How to test Tezz POS

## 1. Automated backend tests
```bash
cd api
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest -q
```
Covers: generic CRUD + company scoping/auth, sync-batch idempotency, pay -> tax/fee
calculation -> fiscal mock -> ERP mock, void/refund, offline-order handling, fiscal
retry, receipt JSON + HTML (SRO 1006 fields, QR, offline-mode label), shift open/close
and Z-report math.

## 2. Web build
```bash
cd web
npm install
npm run build
```
Must exit 0. `npm run dev` for interactive testing against a running api (set
`NEXT_PUBLIC_API_URL`).

## 3. Full stack demo (docker compose)
```bash
cp .env.example .env
docker compose up --build
```
Open `http://localhost:${APP_PORT:-8120}`.

### Demo script
1. **Login**: pick branch "Gulberg", terminal "Terminal 1", PIN `3333` (cashier).
2. **POS**: add a few products (try "Chicken Karahi Full" to see the Spice level /
   Karahi size / Extras modifier dialog), set order type, pick a table, Pay with Cash
   and check the change calculation, then view the printed receipt (FBR fiscal number +
   QR should be present since `FISCAL_PROVIDER=mock` succeeds by default).
3. **Sync page**: toggle "Simulate offline", ring up another order (it stays `LOCAL` /
   pending), toggle back online and watch it sync within ~10s. Also note the 3 "client
   pending" demo orders preloaded on first run.
4. **Force a fiscal failure**: set `FISCAL_MOCK_FAIL_RATE=1` in `.env`, restart the `api`
   container, ring up an order — it pays but shows `fiscal_status=failed`
   ("FBR gateway timeout"). Use the Retry button on `/sync`.
5. **KDS**: open `/kds` in another tab/window, send an order to the kitchen from `/pos`,
   watch the ticket appear grouped by station, use Start/Done.
6. **Shifts**: `/shifts` — open a shift, ring up cash orders, close it and check the
   Z-report (gross sales, tax, Rs.1 fee total, over/short).
7. **Admin**: `/admin` -> API Keys tab shows the live sandbox key; `/admin` -> link out
   to `/api/docs` for the full OpenAPI/Swagger UI.

## 4. API-only testing (Postman / curl)
Import `postman/tezz.postman_collection.json`. See `docs/api-guide.md` for a curl-based
"integrate in 15 minutes" walkthrough, including the webhook HMAC signature format.

## 5. Quick run on your own computer (Windows/Mac/Linux with Docker Desktop)
```bash
git clone https://github.com/khyasir/forge-pos-tezz.git
cd forge-pos-tezz
cp .env.example .env
docker compose up -d --build        # first build takes 3-6 minutes
```
Open http://localhost:8120 (change host port with APP_PORT=8150 docker compose up -d --build).
- API docs: http://localhost:8120/api/docs
- Demo PINs: owner 1111, manager 2222, cashier 3333 (branch Gulberg or DHA)
- Sandbox API key: tz_test_tezzdemo0000000000000001
- Force FBR failures: set FISCAL_MOCK_FAIL_RATE=1 in .env, then `docker compose up -d api`
- Reset demo data: `docker compose down -v && docker compose up -d --build`

If containers cannot reach each other (some locked-down Linux sandboxes), use the host-network override:
`APP_PORT=8120 docker compose -f docker-compose.yml -f docker-compose.hostnet.yml up -d --build`
