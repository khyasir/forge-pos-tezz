# Tezz POS

Fast, FBR/PRA-ready POS for Pakistani restaurants and shops. Offline-first cashier PWA,
a generic REST API, mock fiscal (FBR/PRA) and ERP (Odoo) adapters, webhooks, and a
Sync Status page that proves no order was lost.

See `docs-POS_PLAN.md` for the product plan and `SUMMARY.md` for what was actually built.

## Documentation
- [User guide (owner, manager, cashier)](docs/GUIDE.md)
- [Sync test report](docs/SYNC_TEST_REPORT.md)
- [How to test](docs/HOW_TO_TEST.md)
- [API guide](docs/api-guide.md) and live API docs at `/api/docs`
- [Odoo (WAGS) connector](docs/odoo-wags.md)

## Monorepo layout
```
api/        FastAPI + SQLAlchemy 2 backend (Python 3.12)
web/        Next.js 14 (App Router, TS) PWA cashier UI, Tailwind
docs/       GUIDE.md, SYNC_TEST_REPORT.md, HOW_TO_TEST.md, api-guide.md, odoo-wags.md
e2e/        Playwright end-to-end tests (offline, multi-tab, crash, double-click)
postman/    Postman collection for the REST API
docker-compose.yml, .env.example
```

## Quick start (docker compose)
```bash
cp .env.example .env
docker compose up --build
```
The app seeds demo data on first boot (company "Lahore Karahi House", branches Gulberg/DHA,
PIN logins 1111 owner / 2222 manager / 3333 cashier) and is reachable at
`http://localhost:${APP_PORT:-8120}`. API docs are proxied at
`http://localhost:${APP_PORT:-8120}/api/docs` (Swagger) and `/api/redoc`.

## Quick start (without docker)
Backend:
```bash
cd api
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=sqlite:///./tezz.db uvicorn app.main:app --reload --port 8000
```
Frontend:
```bash
cd web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Tests
```bash
cd api
. .venv/bin/activate
pytest -q
```
Tests run against an in-memory SQLite database, so no Postgres/docker is required.

End-to-end (Playwright, needs the stack running on :8120):
```bash
python -m pytest e2e/test_e2e_pos.py -v
``` See
`docs/HOW_TO_TEST.md` for a fuller test/demo walkthrough.

## Configuration
All configuration is via environment variables, see `.env.example`. Notably:
- `FISCAL_PROVIDER` (`mock` default, or `fbr`) and `FISCAL_MOCK_FAIL_RATE` to exercise the
  retry/offline-mode UI on demand.
- `ERP_PROVIDER` (`mock` default, or `odoo`).
- `DATABASE_URL` — SQLite for local/dev/tests, Postgres in docker-compose.

No secrets are committed; copy `.env.example` to `.env` and fill in real values for a
production deployment (FBR sandbox token, Odoo API key, JWT secret, etc).

## License
MIT (see `LICENSE`). All dependencies are MIT/Apache/BSD licensed.
