"""Regression for "cashier screen shows no products" after an upgrade or a
database reset: a stored login the API no longer accepts must send the
cashier back to the PIN screen, and logging in again must show the catalog.
Run against the running stack:  python3 -m pytest e2e/test_e2e_session.py -v"""
from conftest import login


def test_stale_session_redirects_to_login_then_products_show(ctx):
    page = ctx.new_page()
    login(page)
    assert page.locator("[data-testid=product-tile]").count() >= 30
    # Same as a token minted before `docker compose down -v` / expired token.
    page.evaluate("""() => {
        const s = JSON.parse(localStorage.getItem('tezz_session'));
        s.token = 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJnb25lIn0.stale';
        s.companyId = 'gone';
        localStorage.setItem('tezz_session', JSON.stringify(s));
    }""")
    page.goto(page.url.split("/pos")[0] + "/pos")
    page.wait_for_url("**/login?reason=expired", timeout=15000)
    page.wait_for_selector("[data-testid=session-expired]")
    login(page)
    assert page.locator("[data-testid=product-tile]").count() >= 30


def test_service_worker_is_network_first_for_pages(ctx):
    page = ctx.new_page()
    sw = page.request.get(login.__globals__["BASE"] + "/sw.js").text()
    assert "tezz-pos-shell-v2" in sw
    assert "network first" in sw.lower()
