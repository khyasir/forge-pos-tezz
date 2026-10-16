"""End-to-end tests against the running stack (default http://localhost:8120).
Run from the repo root:  python3 -m pytest e2e/test_e2e_pos.py -v
They use the demo company only (Lahore Karahi House). Nothing is written to Odoo."""
import base64
import os
import time
import urllib.request

from conftest import (API_KEY, BASE, SHOTS, active_ticket_id, add_product, api, local_orders, login,
                      pay_cash, server_orders_by_uuid, sql)

os.makedirs(SHOTS, exist_ok=True)


def wait_for(fn, timeout=40, step=0.5, page=None):
    """Polls fn. When a page is given we wait with page.wait_for_timeout so
    Playwright keeps dispatching route handlers while we wait."""
    end = time.time() + timeout
    while time.time() < end:
        v = fn()
        if v:
            return v
        page.wait_for_timeout(step * 1000) if page else time.sleep(step)
    raise AssertionError("condition not met in time")


def shot(page, name):
    page.screenshot(path=f"{SHOTS}/{name}.png")


def api_text(path):
    req = urllib.request.Request(f"{BASE}/api{path}", headers={"Authorization": f"Bearer {API_KEY}"})
    return urllib.request.urlopen(req).read().decode()


def payments(cid):
    return int(sql(f"select count(*) from payments p join orders o on o.id=p.order_id where o.client_uuid='{cid}'"))


def close_receipt(page):
    page.keyboard.press("Escape")
    if page.locator("text=Receipt").count():
        page.mouse.click(5, 5)


# 1. Product images + placeholder
def test_product_images_and_placeholder(ctx):
    prods = api("GET", "/v1/products?limit=200")
    for name, color, label in [("Fish Tikka", "#f97316", "FISH"), ("Chicken Biryani", "#ca8a04", "BIRYANI")]:
        target = next(p for p in prods if p["name"] == name)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="140"><rect width="200" height="140" fill="#fef3c7"/>'
               f'<circle cx="100" cy="70" r="48" fill="{color}"/><text x="100" y="77" font-family="sans-serif" font-size="18" '
               f'text-anchor="middle" fill="white">{label}</text></svg>')
        api("PUT", f"/v1/products/{target['id']}/image",
            {"data_url": "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()})
    page = ctx.new_page()
    login(page)
    tile = page.locator("[data-testid=product-tile]", has_text="Fish Tikka").first
    assert tile.locator("[data-testid=product-image]").count() == 1
    assert page.locator("[data-testid=product-placeholder]").count() > 0
    page.wait_for_function("[...document.querySelectorAll('[data-testid=product-image]')].every(i => i.complete && i.naturalWidth > 0)")
    shot(page, "01-product-images")


# 2. Park / switch / persist across reload
def test_park_switch_and_reload(ctx):
    page = ctx.new_page()
    login(page)
    add_product(page, "Seekh Kabab (6pc)")
    first_id = active_ticket_id(page)
    page.click("[data-testid=park-order]")
    add_product(page, "Chicken Biryani")
    add_product(page, "Chicken Biryani")
    wait_for(lambda: page.inner_text("[data-testid=open-orders-count]") == "2")
    page.click("[data-testid=open-orders-badge]")
    shot(page, "02-open-orders-menu")
    page.reload()
    page.wait_for_selector("[data-testid=product-tile]")
    wait_for(lambda: page.inner_text("[data-testid=open-orders-count]") == "2")
    page.click("[data-testid=open-orders-badge]")
    rows = page.locator("[data-testid=open-order-row]")
    for i in range(rows.count()):
        if "Seekh" in "" or "(current)" not in rows.nth(i).inner_text():
            rows.nth(i).locator("button").first.click()
            break
    wait_for(lambda: active_ticket_id(page) == first_id)
    shot(page, "03-switched-back-to-parked-order")
    pay_cash(page)
    assert server_orders_by_uuid(first_id) == 1
    close_receipt(page)
    wait_for(lambda: page.inner_text("[data-testid=open-orders-count]") == "1")


# 3. Delivery order: default fee, tax on fee, receipt, server values
def test_delivery_order(ctx):
    page = ctx.new_page()
    login(page)
    add_product(page, "Kabuli Pulao")  # 500
    page.get_by_role("button", name="Delivery", exact=True).click()
    assert page.input_value("[data-testid=delivery-fee]") == "150"
    page.fill("[data-testid=delivery-address]", "House 12, Street 4, Gulberg III")
    shot(page, "04-delivery-order")
    cid = active_ticket_id(page)
    pay_cash(page)
    shot(page, "05-delivery-receipt")
    o = next(x for x in api("GET", "/v1/orders?limit=50") if x["client_uuid"] == cid)
    assert o["order_type"] == "delivery" and o["delivery_fee"] == 150
    assert o["tax_amount"] == round((500 + 150) * 0.16, 2)
    assert o["total"] == round(500 + 150 + o["tax_amount"] + 1, 2)
    html = api_text(f"/v1/orders/{o['id']}/receipt.html")
    assert "Delivery Charges" in html and "Gulberg III" in html


# 4. Offline order -> automatic sync when back online, exactly once
def test_offline_order_syncs_automatically(ctx):
    page = ctx.new_page()
    login(page)
    ctx.set_offline(True)
    add_product(page, "Kabuli Pulao")
    cid = active_ticket_id(page)
    pay_cash(page)
    assert server_orders_by_uuid(cid) == 0
    close_receipt(page)
    page.evaluate("() => { history.pushState({}, '', '/sync'); }")
    page.click("a[href='/sync']")
    page.wait_for_selector("[data-testid=local-row]")
    shot(page, "06-offline-not-synced")
    ctx.set_offline(False)
    wait_for(lambda: server_orders_by_uuid(cid) == 1)
    wait_for(lambda: sql(f"select status||'/'||fiscal_status from orders where client_uuid='{cid}'") == "paid/ok")
    assert sql(f"select offline from orders where client_uuid='{cid}'") == "t"
    wait_for(lambda: any(o["status"] == "SYNCED" for o in local_orders(page) if o["client_uuid"] == cid))
    page.wait_for_timeout(1500)
    shot(page, "07-synced-after-reconnect")
    assert payments(cid) == 1


# 5. Double-click Confirm payment -> one order, one payment
def test_double_click_pay_creates_one_order(ctx):
    page = ctx.new_page()
    login(page)
    add_product(page, "Fish Tikka")
    cid = active_ticket_id(page)
    pay_cash(page, double_click=True)
    time.sleep(2)
    assert server_orders_by_uuid(cid) == 1 and payments(cid) == 1


# 6. Network drops between "create" and "pay": finalized later, once
def test_drop_between_create_and_pay(ctx):
    page = ctx.new_page()
    login(page)
    state = {"n": 0}

    def handler(route):
        state["n"] += 1
        route.abort() if state["n"] == 1 else route.continue_()

    page.route("**/api/v1/orders/*/pay", handler)
    add_product(page, "Malai Boti (6pc)")
    cid = active_ticket_id(page)
    pay_cash(page)
    wait_for(lambda: sql(f"select status from orders where client_uuid='{cid}'") == "paid", timeout=60, page=page)
    wait_for(lambda: any(o["client_uuid"] == cid and o["status"] == "SYNCED" for o in local_orders(page)), timeout=60, page=page)
    assert state["n"] >= 2
    assert server_orders_by_uuid(cid) == 1 and payments(cid) == 1


# 7. Server paid it but the response was lost: client must not pay twice
def test_lost_pay_response_no_double_charge(ctx):
    page = ctx.new_page()
    login(page)
    state = {"n": 0}

    def handler(route):
        state["n"] += 1
        if state["n"] == 1:
            route.fetch()  # reaches the server and is processed
            route.abort()  # ...but the browser never sees the answer
        else:
            route.continue_()

    page.route("**/api/v1/orders/*/pay", handler)
    add_product(page, "Seekh Kabab (6pc)")
    cid = active_ticket_id(page)
    pay_cash(page)
    wait_for(lambda: any(o["client_uuid"] == cid and o["status"] == "SYNCED" for o in local_orders(page)), timeout=60, page=page)
    assert payments(cid) == 1
    assert sql(f"select fiscal_attempts from orders where client_uuid='{cid}'") == "1"


# 8. Two tabs, both offline, both sell; reconnect -> each order exactly once
def test_multi_tab_offline_then_reconnect(ctx):
    a = ctx.new_page()
    login(a)
    b = ctx.new_page()
    b.goto(a.url)
    b.wait_for_selector("[data-testid=product-tile]")
    ctx.set_offline(True)
    add_product(a, "Chicken Biryani")
    ida = active_ticket_id(a)
    pay_cash(a)
    close_receipt(a)
    b.wait_for_timeout(800)  # tab B receives the open-orders broadcast
    add_product(b, "Fish Tikka")
    idb = active_ticket_id(b)
    assert idb != ida
    pay_cash(b)
    ctx.set_offline(False)
    try:
        wait_for(lambda: server_orders_by_uuid(ida) == 1 and server_orders_by_uuid(idb) == 1, timeout=60, page=a)
    except AssertionError:
        print("A", server_orders_by_uuid(ida), "B", server_orders_by_uuid(idb))
        print([(o["client_uuid"][:8], o["status"], o.get("last_error")) for o in local_orders(a) if o["client_uuid"] in (ida, idb)])
        raise
    time.sleep(8)  # more sync ticks in both tabs must not duplicate anything
    for cid in (ida, idb):
        assert server_orders_by_uuid(cid) == 1 and payments(cid) == 1


# 9. Tab closed in the middle of a sync -> recovered by the next tab
def test_crash_mid_sync_recovers(ctx):
    page = ctx.new_page()
    login(page)
    page.evaluate("localStorage.setItem('tezz_stale_syncing_ms', '3000')")
    ctx.set_offline(True)
    add_product(page, "Kabuli Pulao")
    cid = active_ticket_id(page)
    pay_cash(page)
    page.route("**/api/v1/sync/batch", lambda route: None)  # request hangs forever
    ctx.set_offline(False)
    wait_for(lambda: any(o["client_uuid"] == cid and o["status"] == "SYNCING" for o in local_orders(page)), timeout=30, page=page)
    page.close()  # "crash"
    p2 = ctx.new_page()
    login(p2)
    wait_for(lambda: sql(f"select status from orders where client_uuid='{cid}'") == "paid", timeout=60)
    assert server_orders_by_uuid(cid) == 1 and payments(cid) == 1


# 10. Admin: default delivery fee setting + image upload screen
def test_admin_settings_and_images(ctx):
    page = ctx.new_page()
    login(page, pin="1111")
    page.goto(page.url.split("/pos")[0] + "/admin")
    page.get_by_role("button", name="Settings").click()
    page.fill("[data-testid=default-delivery-fee]", "150")
    page.click("[data-testid=save-settings]")
    page.wait_for_selector("text=Saved")
    shot(page, "08-admin-settings")
    page.get_by_role("button", name="Products").click()
    page.wait_for_selector("[data-testid=admin-product-row]")
    shot(page, "09-admin-product-images")
