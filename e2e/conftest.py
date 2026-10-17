import json
import os
import subprocess
import urllib.request

import pytest
from playwright.sync_api import sync_playwright

BASE = os.environ.get("TEZZ_URL", "http://localhost:8120")
API_KEY = os.environ.get("TEZZ_API_KEY", "tz_test_tezzdemo0000000000000001")
COMPOSE_DIR = os.environ.get("TEZZ_COMPOSE_DIR", os.path.expanduser("~/studio/tools/tezz-pos"))
SHOTS = os.environ.get("TEZZ_SHOTS", "/workspace/pos-shots")


def api(method, path, body=None):
    req = urllib.request.Request(
        f"{BASE}/api{path}",
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        txt = r.read().decode()
        return json.loads(txt) if txt else None


def sql(q):
    """Read-only checks against the local Tezz Postgres (never Odoo)."""
    # Defaults match the box's host-network stack; override for a plain
    # `docker compose up` (bridge network): TEZZ_COMPOSE_FILES=docker-compose.yml
    # TEZZ_DB_PORT=5432 and, if needed, TEZZ_COMPOSE_PROJECT=<name>.
    files = os.environ.get("TEZZ_COMPOSE_FILES", "docker-compose.yml,docker-compose.hostnet.yml").split(",")
    cmd = ["docker", "compose"]
    if os.environ.get("TEZZ_COMPOSE_PROJECT"):
        cmd += ["-p", os.environ["TEZZ_COMPOSE_PROJECT"]]
    for f in files:
        cmd += ["-f", f]
    out = subprocess.run(
        cmd + ["exec", "-T", "db", "psql", "-p", os.environ.get("TEZZ_DB_PORT", "5442"), "-U", "tezz", "-At", "-c", q],
        cwd=COMPOSE_DIR, capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture()
def ctx(browser):
    c = browser.new_context(viewport={"width": 1400, "height": 900})
    yield c
    c.close()


def login(page, pin="3333"):
    page.goto(f"{BASE}/login")
    page.wait_for_function("document.querySelectorAll('select option').length > 1")
    for d in pin:
        page.get_by_role("button", name=d, exact=True).click()
    page.wait_for_url("**/pos**")
    page.wait_for_selector("[data-testid=product-tile]")


def active_ticket_id(page):
    return page.evaluate(
        """() => new Promise((res, rej) => {
            const r = indexedDB.open('tezz-pos');
            r.onsuccess = () => {
              const tx = r.result.transaction('meta').objectStore('meta').get('open_orders_v1');
              tx.onsuccess = () => res(tx.result && tx.result.activeId);
              tx.onerror = rej;
            };
        })"""
    )


def local_orders(page):
    return page.evaluate(
        """() => new Promise((res) => {
            const r = indexedDB.open('tezz-pos');
            r.onsuccess = () => {
              const q = r.result.transaction('orders').objectStore('orders').getAll();
              q.onsuccess = () => res(q.result);
            };
        })"""
    )


SIMPLE = ["Seekh Kabab (6pc)", "Chicken Biryani", "Fish Tikka", "Kabuli Pulao", "Malai Boti (6pc)"]


def add_product(page, name="Chicken Biryani"):
    page.locator("[data-testid=product-tile]", has_text=name).first.click()


def pay_cash(page, double_click=False):
    page.locator("button.btn-primary.w-full.text-lg").click()
    page.get_by_role("button", name="Cash", exact=True).click()
    btn = page.get_by_role("button", name="Confirm payment")
    if double_click:
        btn.dblclick()
    else:
        btn.click()
    page.wait_for_selector("text=Receipt", timeout=15000)


def server_orders_by_uuid(client_uuid):
    return int(sql(f"select count(*) from orders where client_uuid='{client_uuid}'"))
