"""Shared fixtures and helpers for the browser tests (Playwright + headless Chromium).

Each test runs the real app on a local port with a fresh database. The BTC price
is fixed at $50,000. Tests are skipped when Playwright or Chromium isn't available;
set PLAYWRIGHT_CHROMIUM to pick a browser binary.
"""
import glob
import os
import threading

import pytest
from werkzeug.serving import make_server

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app import bitcoin, create_app, fx, prices, updates

sync_api = pytest.importorskip('playwright.sync_api')
expect = sync_api.expect

PASSWORD = 'secret12'


def _chromium_path():
    if os.environ.get('PLAYWRIGHT_CHROMIUM'):
        return os.environ['PLAYWRIGHT_CHROMIUM']
    patterns = [
        '~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell',
        '~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell',
    ]
    found = sorted(path for p in patterns for path in glob.glob(os.path.expanduser(p)))
    return found[-1] if found else None  # None -> Playwright's own default browser


@pytest.fixture(scope='module')
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch(executable_path=_chromium_path())
        except Exception as e:  # no browser installed
            pytest.skip(f'Chromium not available: {e}')
        yield b
        b.close()


HISTORY_DAYS = 400


def utc_today():
    return datetime.now(timezone.utc).date()


def days_ago(n):
    return (utc_today() - timedelta(days=n)).isoformat()


def fake_closes(start, end):
    """Fake price history: the last 400 finished days, rising $25 a day to $40,000 yesterday"""
    first = max(start, end - timedelta(days=HISTORY_DAYS - 1))
    out, day = [], first
    while day <= end:
        out.append((day, Decimal('40000') - 25 * (end - day).days))
        day += timedelta(days=1)
    return out


def fake_rates(start, end):
    """Fake exchange rates: 1 USD = R$5 = €0.90 = £0.80 every day"""
    out, day = [], start
    while day <= end:
        out += [(day, 'BRL', Decimal('5')), (day, 'EUR', Decimal('0.90')), (day, 'GBP', Decimal('0.80'))]
        day += timedelta(days=1)
    return out


@pytest.fixture
def base_url(tmp_path, monkeypatch):
    """Run the app on a free local port with a fresh database"""
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setattr(bitcoin, '_fetch_bitcoin_price', lambda: 50000.0)
    bitcoin._price_cache.update(price=None, fetched_at=0.0)
    prices._state['last_failure'] = 0.0
    fx.reset_state()
    updates.reset_cache()
    monkeypatch.setattr(prices, 'fetch_closes', fake_closes)
    monkeypatch.setattr(fx, 'RATES_START', utc_today() - timedelta(days=1200))
    monkeypatch.setattr(fx, 'fetch_rates', fake_rates)
    app = create_app({'TESTING': True, 'DATABASE': str(tmp_path / 'e2e.sqlite')})
    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown()


@pytest.fixture
def page(browser, base_url):
    context = browser.new_context(viewport={'width': 1280, 'height': 900})
    pg = context.new_page()
    pg.set_default_timeout(5000)
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    yield pg
    context.close()
    assert errors == [], f'JavaScript errors: {errors}'


def sign_in(page, base_url):
    page.request.post(f'{base_url}/auth/register',
                      form={'username': 'alice', 'email': 'alice@example.com', 'password': PASSWORD})
    page.request.post(f'{base_url}/auth/login', form={'username': 'alice', 'password': PASSWORD})
    page.request.get(f'{base_url}/auth/register')  # use up flash messages so no popup covers the page


def add_trade(page, base_url, **fields):
    response = page.request.post(f'{base_url}/api/trades', data=fields)
    assert response.status == 201, response.text()
    return response.json()['trade']['id']


def open_dashboard(page, base_url):
    page.goto(f'{base_url}/')
    expect(page.locator('#btc-price span')).to_have_text('$50,000.00')


